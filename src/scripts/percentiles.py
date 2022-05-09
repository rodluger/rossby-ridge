#!/usr/bin/env python
# coding: utf-8

import paths
import numpy as np
import pandas as pd

from astropy.table import Table

import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams["figure.dpi"] = 100
mpl.rcParams["savefig.bbox"] = "tight"
mpl.rcParams["savefig.dpi"] = 300

import seaborn as sns


sun = {"teff": 5772,
       "prot":26.09,
       "e_prot":26.09-24.5,
       "E_prot":27-26.09
      }


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

def ridge_hi(teff):
    m = (2-24)/(6500-5800)
    b = (2 - m*6500) 
    return m*teff + b

def ridge_lo(teff):
    m = (2-24)/(6500-5800)
    b = (-5 - m*6500) 
    return m*teff + b

mask = (cks['p20_cks_slogg']>4) #main sequence
ridge = (cks['p20_cks_steff']>5850)
ridge &= (cks['p20_cks_steff']<6500)
ridge &= (cks['d21_prot']<ridge_hi(cks['p20_cks_steff']))
ridge &= (cks['d21_prot']>ridge_lo(cks['p20_cks_steff']))
ridge &= mask
######################################################################################


######################################################################################
# LAMOST-Kepler 
lam = pd.read_parquet(paths.data / 'kepler_lamost.parquet')
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

def convective_turnover_timescale(teff):
    #Returns convective turnover timescale in days
    return 314.24*np.exp(-(teff/1952.5) - (teff/6250.)**18.) + 0.002


lam["Ro"] = lam["Prot"]/convective_turnover_timescale(lam["Teff_lam"])    
      
def percentile_bootstrap(nsamples=100, f=0.5, pctl=90.):
    
    _teff = np.linspace(4000,7500,1000)
    teff_bin_centers = np.arange(4000,7020,20)    
    
    per_pctl = np.zeros(len(teff_bin_centers))
    per_pctl_err = np.zeros(len(teff_bin_centers))
    
    for i, tc in enumerate(teff_bin_centers):
        arg = (abs(lam["Teff_lam"]-tc)<100) & (lam["Ro"]<5/3)
        pctl_arr = []
        
        for n in range(nsamples):
            _x = np.array(lam["Prot"][arg])
            pctl_arr.append(np.nanpercentile(_x[np.random.choice(len(_x), int(f*len(_x)), replace=True)], pctl))
        
        per_pctl[i] = np.mean(pctl_arr)
        per_pctl_err[i] = np.std(pctl_arr)    
        
        
    return per_pctl, per_pctl_err
    
    
period_90th_pctl, e_period_90th_pctl = percentile_bootstrap(pctl=90.)
period_10th_pctl, e_period_10th_pctl = percentile_bootstrap(pctl=10.)    


sns.set(font_scale=1.7, context="paper", style="ticks", palette="Blues")

teff_bin_centers = np.arange(4000,7020,20)
roc_period_90th_pctl = np.zeros(len(teff_bin_centers))
roc_period_10th_pctl = np.zeros(len(teff_bin_centers))

std_period_90th_pctl = np.zeros(len(teff_bin_centers))
std_period_10th_pctl = np.zeros(len(teff_bin_centers))

for i, tc in enumerate(teff_bin_centers):
    roc_arg = (abs(roc["Teff"]-tc)<100)
    roc_period_90th_pctl[i] = np.nanpercentile(roc["period"][roc_arg], 90.)
    roc_period_10th_pctl[i] = np.nanpercentile(roc["period"][roc_arg], 10.)
    
    std_arg = (abs(std["Teff"]-tc)<100)
    std_period_90th_pctl[i] = np.nanpercentile(std["period"][std_arg], 90.)
    std_period_10th_pctl[i] = np.nanpercentile(std["period"][std_arg], 10.)    
        
plt.plot(teff_bin_centers, std_period_90th_pctl, color='C2', label='Standard model', lw=6, alpha=0.5)
plt.plot(teff_bin_centers, roc_period_90th_pctl, color='C5', label='WMB model', lw=3, alpha=0.5, ls='--')
plt.scatter(teff_bin_centers, period_90th_pctl, color='k', label='LAMOST–McQuillan', s=2)
plt.plot(cks['cks_Teff'][ridge], cks['d21_prot'][ridge], 'o', mfc='None', mec='k', ms=4, mew=0.5, alpha=0.5, label='CKS long-period pile-up')

plt.plot(teff_bin_centers, roc_period_10th_pctl, color='C2', lw=6, alpha=0.5)
plt.plot(teff_bin_centers, std_period_10th_pctl, color='C5', lw=3, alpha=0.5, ls='--')
plt.scatter(teff_bin_centers, period_10th_pctl, color='k', s=2)
plt.xlim(7000,4500)
plt.xlabel("Effective temperature [K]")
plt.ylabel("Rotation period [d]")
plt.legend(prop={'size':13})
sns.despine()
plt.savefig(paths.figures / 'percentiles.pdf')

arg = (teff_bin_centers<6250) & (teff_bin_centers>4500)
chisq_roc = np.sum((period_90th_pctl[arg] - roc_period_90th_pctl[arg])**2 / roc_period_90th_pctl[arg])
chisq_std = np.sum((period_90th_pctl[arg] - std_period_90th_pctl[arg])**2 / std_period_90th_pctl[arg])

print('WMB model chi-squared      :', chisq_roc)
print('Standard model chi-squared :', chisq_std)
print('(Standard-WMB) chi-squared :', chisq_std-chisq_roc)
