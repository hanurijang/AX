#!/usr/bin/env python3
"""Recreate M31 teaching posteriors, retaining full unrounded chains.

Normal: independent group means U(0,1000), shared SD U(0,100).
Poisson: a U(-10,10), b U(-5,5). These match the old source comment.
NumPy PCG64 streams are derived from a fixed SeedSequence; no seed selection.
"""
import gzip,hashlib,json,re
from pathlib import Path
import numpy as np
import scipy
from scipy import optimize,stats,integrate
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/visual_stage2'
SEED=20261104; WARMUP=1000; DRAWS=5000; CHAINS=5

def array(name):
 s=next((ROOT/'module_v1').glob('M31*')).read_text();m=re.search(r'\b'+name+r'\s*=\s*(?=\[)',s)
 return np.array(json.JSONDecoder().raw_decode(s[m.end():])[0],dtype=float)

def split(a):
 n=a.shape[1]//2;return np.concatenate([a[:,:n],a[:,-n:]])

def rhat(a):
 a=split(a);n=a.shape[1];W=np.var(a,axis=1,ddof=1).mean();B=n*np.var(a.mean(axis=1),ddof=1)
 return float(np.sqrt(((n-1)*W/n+B/n)/W))

def rankz(a):
 r=stats.rankdata(a.ravel()).reshape(a.shape)
 return stats.norm.ppf((r-.375)/(a.size+.25))

def ess(a):
 a=split(a);m,n=a.shape;center=a-a.mean(axis=1,keepdims=True)
 size=1<<(2*n-1).bit_length();f=np.fft.rfft(center,n=size)
 acov=np.fft.irfft(f*np.conjugate(f),n=size)[:,:n]/n
 W=(acov[:,0]*n/(n-1)).mean();varplus=W*(n-1)/n+np.var(a.mean(axis=1),ddof=1)
 rho=1-(W-acov.mean(axis=0))/varplus;rho[0]=1
 pairs=[]
 for t in range(0,n-1,2):
  pair=float(rho[t]+rho[t+1])
  if pair<0:break
  pairs.append(min(pair,pairs[-1]) if pairs else pair)
 tau=max(1/np.log10(m*n),-1+2*sum(pairs))
 return float(min(m*n,np.prod(a.shape)/tau))

def diagnostic(a):
 z=rankz(a);fold=rankz(abs(a-np.median(a)));q=np.quantile(a,[.05,.95])
 return {'rhat':max(rhat(z),rhat(fold)),'ess_bulk':ess(z),
         'ess_tail':min(ess((a<=q[0]).astype(float)),ess((a>=q[1]).astype(float))),
         'mean':float(a.mean()),'quantile95':np.quantile(a,[.025,.975]).tolist()}

def normal_chains(a,b):
 groups=[a,b];rng=np.random.default_rng(np.random.SeedSequence([SEED,1]))
 state=np.empty((CHAINS,3));state[:,0]=[300,800,525,245,900];state[:,1]=[800,300,585,149,900];state[:,2]=np.log(20)
 full=np.empty((CHAINS,WARMUP+DRAWS+1,3));full[:,0]=state
 accepted=np.zeros(CHAINS);attempts=np.zeros(CHAINS);step=np.ones(CHAINS)*.3
 for t in range(1,WARMUP+DRAWS+1):
  ls=state[:,2];ss_mu=np.zeros(CHAINS)
  for g,y in enumerate(groups):
   n=len(y);mean=y.mean();ss=np.sum((y-mean)**2)
   mu=rng.normal(mean,np.exp(ls)/np.sqrt(n));bad=(mu<0)|(mu>1000)
   while bad.any():mu[bad]=rng.normal(mean,np.exp(ls[bad])/np.sqrt(n));bad=(mu<0)|(mu>1000)
   state[:,g]=mu;ss_mu+=ss+n*(mu-mean)**2
  prop=ls+rng.normal(0,step)
  # Both groups share sigma. Jacobian for log sigma contributes +log sigma.
  logratio=-(len(a)+len(b)-1)*(prop-ls)-ss_mu*.5*(np.exp(-2*prop)-np.exp(-2*ls))
  ok=(prop<np.log(100))&(np.log(rng.random(CHAINS))<logratio)
  state[ok,2]=prop[ok];accepted+=ok;attempts+=1
  if t<=WARMUP and t%50==0:
   step*=np.exp((accepted/attempts-.44)*.5);accepted[:]=0;attempts[:]=0
  if t==WARMUP:accepted[:]=0;attempts[:]=0
  full[:,t]=state
 full[:,:,2]=np.exp(full[:,:,2])
 return full,(accepted/attempts).tolist(),step.tolist()

def poisson_chains(x,y):
 center=float(x.mean());scale=float(x.std(ddof=1));z=(x-center)/scale;X=np.column_stack([np.ones(len(x)),z])
 mle=optimize.minimize(lambda v:float(np.sum(np.exp(X@v)-y*(X@v))),[np.log(y.mean()),0],jac=lambda v:X.T@(np.exp(X@v)-y),method='BFGS')
 cov=np.linalg.inv(X.T@(np.exp(X@mle.x)[:,None]*X));chol=np.linalg.cholesky(cov)*2.38/np.sqrt(2)
 rng=np.random.default_rng(np.random.SeedSequence([SEED,2]));v=mle.x+rng.normal(size=(CHAINS,2))@chol.T*2
 def logp(q):
  b=q[:,1]/scale;a=q[:,0]-b*center;eta=q@X.T
  return np.where((abs(a)<10)&(abs(b)<5),np.sum(y*eta-np.exp(eta),axis=1),-np.inf)
 lp=logp(v);full=np.empty((CHAINS,WARMUP+DRAWS+1,2));full[:,0]=v
 accepted=np.zeros(CHAINS);attempts=np.zeros(CHAINS);factor=np.ones(CHAINS)
 for t in range(1,WARMUP+DRAWS+1):
  proposal=v+(rng.normal(size=(CHAINS,2))@chol.T)*factor[:,None];new=logp(proposal)
  ok=np.log(rng.random(CHAINS))<new-lp;v[ok]=proposal[ok];lp[ok]=new[ok];accepted+=ok;attempts+=1
  if t<=WARMUP and t%50==0:
   factor*=np.exp((accepted/attempts-.234)*.5);accepted[:]=0;attempts[:]=0
  if t==WARMUP:accepted[:]=0;attempts[:]=0
  full[:,t]=v
 b=full[:,:,1]/scale;a=full[:,:,0]-b*center
 return np.stack([a,b],axis=2),(accepted/attempts).tolist(),{'center':center,'scale':scale,'proposal_cholesky':chol.tolist(),'final_factor':factor.tolist()}

def save(name,data):
 raw=json.dumps(data,separators=(',',':'),allow_nan=False).encode();content=gzip.compress(raw,mtime=0)
 (OUT/name).write_bytes(content);return hashlib.sha256(content).hexdigest()

def main():
 OUT.mkdir(exist_ok=True,parents=True);ga,gb,fx,fy=[array(n) for n in ['GA','GB','FX','FY']]
 normal,nacc,nstep=normal_chains(ga,gb);pois,pacc,pconfig=poisson_chains(fx,fy)
 n=normal[:,WARMUP+1:];p=pois[:,WARMUP+1:];delta=n[:,:,1]-n[:,:,0]
 diagnostics={name:diagnostic(v) for name,v in [('muA',n[:,:,0]),('muB',n[:,:,1]),('sigma',n[:,:,2]),('delta',delta),('a',p[:,:,0]),('b',p[:,:,1])]}
 assert all(d['rhat']<1.01 and d['ess_bulk']>400 and d['ess_tail']>400 for d in diagnostics.values()),diagnostics
 edges=np.arange(np.floor(delta.min()),np.ceil(delta.max())+1);hist=np.histogram(delta,edges)[0]
 # Exact marginal SD integration provides a separate check for the normal posterior.
 # Integrating two nearly untruncated means adds two powers of SD; distant mean bounds
 # have negligible mass for these data (means >500, SD<=100).
 independent={}
 for name,y in [('muA',ga),('muB',gb)]:
  ss=sum(np.sum((g-g.mean())**2) for g in [ga,gb]);N=len(ga)+len(gb);power=N-2;mode=np.sqrt(ss/power);offset=-power*np.log(mode)-ss/(2*mode**2)
  weight=lambda sd:np.exp(-power*np.log(sd)-ss/(2*sd**2)-offset) if sd>0 else 0
  mass=integrate.quad(weight,0,100,epsabs=1e-10)[0]
  variance=integrate.quad(lambda sd:weight(sd)*sd*sd/len(y),0,100,epsabs=1e-10)[0]/mass
  independent[name]={'mean':float(y.mean()),'variance':variance}
  assert abs(diagnostics[name]['mean']-y.mean())<.25
  assert abs(np.var(n[:,:,0 if name=='muA' else 1])/variance-1)<.1
 tail={str(k):float((delta>k).mean()) for k in [0,5,10,15,20]}
 a_hist=np.histogram(p[:,:,0],bins=40);b_hist=np.histogram(p[:,:,1],bins=40)
 summary={'seed':SEED,'warmup':WARMUP,'draws_per_chain':DRAWS,'chains':CHAINS,'retained_count':int(delta.size),
 'diagnostics':diagnostics,'delta':{'histogram':hist.tolist(),'edges':edges.tolist(),'probabilities':tail},
 'poisson':{'a_hist':a_hist[0].tolist(),'a_edges':a_hist[1].tolist(),'b_hist':b_hist[0].tolist(),'b_edges':b_hist[1].tolist()},
 'trace':{'stride':10,'steps':list(range(0,WARMUP+DRAWS+1,10)),'muA':normal[:,::10,0].tolist(),'muB':normal[:,::10,1].tolist()},
 'normal_model':{'likelihood':'independent Normal(mu_g,sigma) observations with shared sigma','mu_prior':'Uniform(0,1000)','sigma_prior':'Uniform(0,100)','sampler':'Gibbs mu, random walk Metropolis log sigma including Jacobian; warmup-only proposal adaptation','acceptance':nacc,'final_log_sigma_steps':nstep},
 'poisson_model':{'likelihood':'Poisson(exp(a+b*x))','a_prior':'Uniform(-10,10)','b_prior':'Uniform(-5,5)','sampler':'joint random walk Metropolis in centered/scaled x coordinates; warmup-only adaptation','acceptance':pacc,**pconfig},
 'independent_normal_integral':independent,'software':{'numpy':np.__version__,'scipy':scipy.__version__,'rng':'PCG64'},
 'data':{'GA':ga.tolist(),'GB':gb.tolist(),'FX':fx.tolist(),'FY':fy.tolist()},'source_note':'New reproducible teaching calculation; not recovery of original chains. Priors follow the previous module source comment.'}
 summary['full_chain_files']={'m31_normal_chains.json.gz':save('m31_normal_chains.json.gz',{'columns':['muA','muB','sigma'],'includes_initial_state':True,'warmup':WARMUP,'chains':normal.tolist()}),'m31_poisson_chains.json.gz':save('m31_poisson_chains.json.gz',{'columns':['a','b'],'includes_initial_state':True,'warmup':WARMUP,'chains':pois.tolist()})}
 (OUT/'m31_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:{q:round(d[q],3) if isinstance(d[q],float) else d[q] for q in ['mean','quantile95','rhat','ess_bulk','ess_tail']} for k,d in diagnostics.items()},indent=2))
 assert hist.sum()==delta.size and sum(a_hist[0])==p[:,:,0].size and sum(b_hist[0])==p[:,:,1].size

if __name__=='__main__':main()
