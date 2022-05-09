#!/usr/bin/env python
# coding: utf-8

import paths
import numpy as np
import pandas as pd
import astropy.constants as c
from astropy.table import Table

import matplotlib.pyplot as plt
import matplotlib as mpl


mpl.rcParams["figure.dpi"] = 100
mpl.rcParams["savefig.bbox"] = "tight"
mpl.rcParams["savefig.dpi"] = 300

import seaborn as sns

####################################################################
# The Sun
sun = {"teff": 5772,
       "prot": 25.4,
       "e_prot": 25.4-24.5,
       "E_prot": 27-25.4
      }

sun["logg"] = np.log10(c.GM_sun.cgs.value/c.R_sun.cgs.value**2)
####################################################################


######################################################################################
#McQuillan et al. 2013
mcq_koi = Table.read("https://cdsarc.cds.unistra.fr/ftp/J/ApJ/775/L11/table1.dat",
                readme="https://cdsarc.cds.unistra.fr/ftp/J/ApJ/775/L11/ReadMe",
                format="ascii.cds")
mcq_koi = mcq_koi.to_pandas()
mcq_koi = mcq_koi.add_prefix('mcq_')


#McQuillan et al. 2014
mcq = pd.read_parquet(paths.data / 'mcquillan2014_table1.parquet')
######################################################################################


######################################################################################
# California-Kepler Survey (Fulton & Petigura 2018)
# This data table has been augmented with data from other surveys (see David et al. 2021)
cks = pd.read_parquet(paths.data / 'cks_merged.parquet')
# The dataframe has a row entry for each KOI, meaning individual star are represented N times
# where N is the number of KOIs detected around that star so we drop duplicates.
cks = cks.drop_duplicates(subset=['kepid'], keep='first')
cks = cks.merge(mcq_koi, how='left', left_on='kepid', right_on='mcq_KIC')
# Filter stars that have discrepant Teff between CKS and SPOCS
#cks_mask = abs(cks['cks_Teff']-cks['bf18_Teff'])/cks['cks_Teff'] < 0.02
######################################################################################


######################################################################################
# LAMOST-Kepler 
lam = pd.read_csv(paths.data / 'kepler_lamost.csv')
print('LAMOST unique KIC targets:', len(np.unique(lam["KIC"])))
print('LAMOST unique DR2 targets:', len(np.unique(lam["DR2Name"])))

# Drop duplicate sources, keeping the one with the brighter G magnitude
lam = lam.sort_values(["KIC", "Gmag"], ascending = (True, True))
lam = lam.merge(mcq, how='left', left_on="KIC", right_on="mcq_KIC")
lam = lam.drop_duplicates(subset=['KIC'], keep='first')

lam_mask = (lam["Teff_lam"]>3000)
lam_mask = (lam["Teff_lam"]<8000)
lam_mask &= (lam["logg_lam"]>3)
lam_mask &= (lam["logg_lam"]<5)
lam_mask &= (abs(lam["feh_lam"])<2)
lam = lam[lam_mask]

print('LAMOST unique KIC targets:', len(np.unique(lam["KIC"])))
print('LAMOST unique DR2 targets:', len(np.unique(lam["DR2Name"])))
print('Median LAMOST Teff error:', np.median(lam["e_Teff_lam"]))
######################################################################################

######################################################################################
# van Saders et al. 2019 models
std = pd.read_hdf(paths.data / 'standard_population.h5', key='sample')
std = std[std['evo']==1]

roc = pd.read_hdf(paths.data / 'rocrit_population.h5', key='sample')
roc = roc[roc['evo']==1]

std['flag'] = 'std'
roc['flag'] = 'roc'

model = pd.concat([std, roc], ignore_index=True, sort=True)
######################################################################################

cks_shift = 111
lamost_shift = 116

#Detrending LAMOST Teff
# def lamost_teff_detrend(teff):   
#     dteff = 2.55513439e-13*teff**5 - 7.18129973e-09*teff**4 + 8.04175914e-05*teff**3 - 4.48417848e-01*teff**2 + 1.24490338e+03*teff - 1.37649898e+06
#     return teff-dteff

# lam["Teff_lam"] = lamost_teff_detrend(lam["Teff_lam"])


mpl.rcParams["legend.markerscale"] = 1
sns.set(font_scale=1.2, context="paper", style="ticks")
sc_kws = {"marker":",", "color":"orange", "s":8, "rasterized":True}
sun_kws = {"marker":"o", "color":"black", "ms":8, "mfc":"None", "mew":1}

#sns.displot(data=std, x="Teff(K)", y="Prot(days)", binwidth=(20, 0.5), cbar=True, cbar_kws={'label': r'N$_\mathregular{stars}$'})

#We only want to plot dwarf stars
logg_thresh = 4.1
cks_ms = cks['p20_cks_slogg'] > logg_thresh
lam_ms = lam['logg_lam'] > logg_thresh

sns.displot(data=std, x="Teff", y="period", binwidth=(20, 0.5), cbar=True, vmin=0, vmax=100, cbar_kws={'label': r'N$_\mathregular{stars}$'})
plt.scatter(cks['cks_Teff'][cks_ms]+cks_shift, cks['d21_prot'][cks_ms], label='California–Kepler Survey', **sc_kws)
plt.plot(sun["teff"], sun["prot"], **sun_kws)
plt.plot(sun["teff"], sun["prot"], 'k.')
plt.gca().invert_xaxis()
plt.xlim(6500,5000)
plt.ylim(0,50)
plt.legend(loc='upper left', prop={"size":10})
plt.title('Standard model')
plt.xlabel('Effective temperature [K]')
plt.ylabel('Rotation period [d]')
plt.text(1.15,1.05,"a",transform=plt.gca().transAxes,weight="bold",size=14)
plt.savefig(paths.figures / 'std-model-cks-shifted.pdf')


sns.displot(data=roc, x="Teff", y="period", binwidth=(20, 0.5), cbar=True, vmin=0, vmax=100, cbar_kws={'label': r'N$_\mathregular{stars}$'})
plt.scatter(cks['cks_Teff'][cks_ms]+cks_shift, cks['d21_prot'][cks_ms], label='California–Kepler Survey', **sc_kws)
plt.plot(sun["teff"], sun["prot"], **sun_kws)
plt.plot(sun["teff"], sun["prot"], 'k.')
plt.gca().invert_xaxis()
plt.xlim(6500,5000)
plt.ylim(0,50)
plt.legend(loc='upper left', prop={"size":10})
plt.title('Weakened magnetic braking model')
plt.xlabel('Effective temperature [K]')
plt.ylabel('Rotation period [d]')
plt.text(1.15,1.05,"b",transform=plt.gca().transAxes,weight="bold",size=14)
plt.savefig(paths.figures / 'wmb-model-cks-shifted.pdf')

mpl.rcParams["legend.markerscale"] = 5
sns.set(font_scale=1.2, context="paper", style="ticks")
sc_kws = {"marker":",", "color":"orange", "s":1, "rasterized":True, "alpha":0.75}


sns.displot(data=std, x="Teff", y="period", binwidth=(20, 0.5), cbar=True, vmin=0, vmax=100, cbar_kws={'label': r'N$_\mathregular{stars}$'})
plt.scatter(lam['Teff_lam'][lam_ms]+lamost_shift, lam['Prot'][lam_ms], label='LAMOST–McQuillan', **sc_kws)
plt.plot(sun["teff"], sun["prot"], **sun_kws)
plt.plot(sun["teff"], sun["prot"], 'k.')
plt.gca().invert_xaxis()
plt.xlim(6500,5000)
plt.ylim(0,50)
plt.legend(loc='upper left', prop={"size":10})
plt.title('Standard model')
plt.xlabel('Effective temperature [K]')
plt.ylabel('Rotation period [d]')
plt.text(1.15,1.05,"c",transform=plt.gca().transAxes,weight="bold",size=14)
plt.savefig(paths.figures / 'std-model-lamost-shifted.pdf')


sns.displot(data=roc, x="Teff", y="period", binwidth=(20, 0.5), cbar=True, vmin=0, vmax=100, cbar_kws={'label': r'N$_\mathregular{stars}$'})
plt.scatter(lam['Teff_lam'][lam_ms]+lamost_shift, lam['Prot'][lam_ms], label='LAMOST–McQuillan', **sc_kws)
plt.plot(sun["teff"], sun["prot"], **sun_kws)
plt.plot(sun["teff"], sun["prot"], 'k.')
plt.gca().invert_xaxis()
plt.xlim(6500,5000)
plt.ylim(0,50)
plt.legend(loc='upper left', prop={"size":10})
plt.title('Weakened magnetic braking model')
plt.xlabel('Effective temperature [K]')
plt.ylabel('Rotation period [d]')
plt.text(1.15,1.05,"d",transform=plt.gca().transAxes,weight="bold",size=14)
plt.savefig(paths.figures / 'wmb-model-lamost-shifted.pdf')
