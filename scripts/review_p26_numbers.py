#!/usr/bin/env python3
"""26차: 소스의 가상 자료를 독립적인 NumPy/SciPy 식으로 대조한다.
python scripts/review_p26_numbers.py --output /tmp/ax-review/numbers.json
MCMC 원표집·과거 모의실험의 생성 과정 재현은 범위 밖이다.
"""
import argparse,itertools,json,re
from pathlib import Path
import numpy as np
from scipy import stats,optimize,special,integrate
ROOT=Path(__file__).resolve().parents[1];results=[]
def src(n):return next((ROOT/'module_v1').glob(f'M{n:02}_*')).read_text().split('<script>')[-1]
def arr(n,name):
 s=src(n);m=re.search(r'\b'+name+r'\s*=\s*(\[)',s);assert m,(n,name)
 return np.array(json.JSONDecoder().raw_decode(s[m.start(1):])[0],dtype=float)
def check(module,label,actual,expected,tol):
 a=np.asarray(actual);e=np.asarray(expected);assert np.allclose(a,e,atol=tol,rtol=0),(module,label,a,e)
 results.append({'module':module,'check':label,'actual':a.tolist(),'expected':e.tolist(),'tolerance':tol})
def ols(y,*xs):
 X=np.column_stack([np.ones(len(y)),*xs]);b=np.linalg.lstsq(X,y,rcond=None)[0];r=y-X@b;return b,r,X

def main():
 a=argparse.ArgumentParser();a.add_argument('--output',type=Path,default=Path('/tmp/ax-review/numbers.json'));args=a.parse_args()
 check('M01','12 values mean',np.mean([1.2,2.1,2.1,.8,2.4,.7,1.6,1.3,.9,4.2,2,1]),20.3/12,1e-12)
 check('M02','blood pressure means',[np.mean([125,145,105,140,110]),np.mean([130,170,135,165,150])],[125,150],1e-12)
 check('M03','census cost and days',[50000000*100,100000/100],[5000000000,1000],0)
 h=arr(4,'HEIGHTS');check('M04','165<=height<170 count',np.sum((h>=165)&(h<170)),33,0)
 income=arr(5,'incomes');after=np.append(income,100000)
 check('M05','defined town mean/median before and after',[income.mean(),np.median(income),after.mean(),np.median(after)],[5088,5088,6027.722772277,5091],1e-6)
 check('M05','100 income observations',len(income),100,0)
 check('M06','two-value payout mean/variance',[.8*100+.2*500,.8*(100-180)**2+.2*(500-180)**2],[180,25600],1e-12)
 check('M07','normal mass within 1,2,3 SD',2*stats.norm.cdf([1,2,3])-1,[.682689,.954500,.997300],1e-6)
 sample=arr(9,'SAMPLE10');check('M08–10','sample mean, centered SS, sample SD',[sample.mean(),np.sum((sample-sample.mean())**2),sample.std(ddof=1)],[167.9,426.9,6.887186],1e-5)
 check('M10','coverage of +/-2SE at df9',stats.t.cdf(2,9)-stats.t.cdf(-2,9),.923447,1e-6)
 drug=arr(14,'DRUG');plac=arr(14,'PLAC');pool=np.r_[drug,plac];obs=drug.mean()-plac.mean();ext=0
 for ix in itertools.combinations(range(14),7):
  sa=pool[list(ix)].sum();d=sa/7-(pool.sum()-sa)/7;ext+=abs(d)>=abs(obs)-1e-10
 check('M11','exact randomization tail count',ext,70,0)
 t=stats.ttest_ind(drug,plac,equal_var=True);check('M12','pooled t and two-sided p',[t.statistic,t.pvalue],[-2.729,.0183],.0005)
 power=lambda n,d:stats.nct.sf(stats.t.ppf(.975,2*n-2),2*n-2,d*np.sqrt(n/2))+stats.nct.cdf(-stats.t.ppf(.975,2*n-2),2*n-2,d*np.sqrt(n/2))
 check('M13','minimum group sizes for 80% power',[next(n for n in range(2,100) if power(n,d)>=.8) for d in [.5,1,2]],[64,17,6],0)
 check('M14','Shapiro p values',[stats.shapiro(drug).pvalue,stats.shapiro(plac).pvalue],[.135,.489],.001)
 check('M14','paired t',stats.ttest_rel(drug,arr(14,'BEFORE')).statistic,-7.77,.01)
 groups=[arr(15,n) for n in ['FA','FB','FC']];check('M15','ANOVA F',stats.f_oneway(*groups).statistic,60.675,.002)
 check('M16','binomial exact two-sided p',stats.binomtest(21,30,.5).pvalue,.04277,.00001)
 check('M16','die chi-square',[stats.chisquare([5,8,10,20,7,10]).statistic,stats.chisquare([5,8,10,20,7,10]).pvalue],[13.8,.01693],.00002)
 x=arr(17,'MATH');y=arr(17,'SCI');check('M17','Pearson, Spearman, Kendall',[stats.pearsonr(x,y).statistic,stats.spearmanr(x,y).statistic,stats.kendalltau(x,y).statistic],[.927,.91,.81],.005)
 b,r,X=ols(y,x);check('M18','OLS coefficients, SSE, R2',[*b,r@r,1-(r@r)/np.sum((y-y.mean())**2)],[16.1396,.72911,162.365,.859607],.001)
 b,r,X=ols(arr(19,'WT'),arr(19,'HT'),arr(19,'WS'));check('M19','multiple regression coefficients',b,[-66.8,.538,.535],.05)
 check('M20','interaction contrasts',[32-13,35-30,(35-30)-(32-13)],[19,5,-14],0)
 bx=arr(21,'BX');by=arr(21,'BY');X=np.column_stack([np.ones(len(bx)),bx]);fit=optimize.minimize(lambda b:np.sum(np.logaddexp(0,X@b)-by*(X@b)),np.zeros(2),jac=lambda b:X.T@(special.expit(X@b)-by),method='BFGS',options={'gtol':1e-9})
 check('M21','logistic MLE',fit.x,[-4.48,.877],.005)
 fx=arr(22,'FX');fy=arr(22,'FY');X=np.column_stack([np.ones(len(fx)),fx]);fit=optimize.minimize(lambda b:np.sum(np.exp(X@b)-fy*(X@b)),[0,0],jac=lambda b:X.T@(np.exp(X@b)-fy),method='BFGS',options={'gtol':1e-9});ll=np.sum(stats.poisson.logpmf(fy,np.exp(X@fit.x)))
 check('M22','Poisson MLE',fit.x,[-2.54,.577],.005)
 check('M23','Poisson log likelihood, AIC, BIC',[ll,-2*ll+4,-2*ll+2*np.log(20)],[-32.15,68.3,70.3],.04)
 check('M24','significance re-detection ratio',35/97,.360825,1e-6)
 sp=np.sqrt((16*10.2**2+16*9.6**2)/32);d=9/sp;check('M25','d and approximate Hedges g',[d,(1-3/(4*32-1))*d],[.91,.89],.005)
 se2=200/20;B=stats.norm.pdf(7,0,np.sqrt(se2+100))/stats.norm.pdf(7,0,np.sqrt(se2));check('M26','normal-prior Bayes factor',B,2.8,.01)
 check('M26','mixture false positive probability',.9*.05/(.9*.05+.1*.8),.36,1e-12)
 check('M27','FWER for 20 independent null tests',1-.95**20,.641514,1e-6)
 b,r,X=ols(arr(28,'CY'),arr(28,'CX'),arr(28,'CZ'));check('M28','adjusted education coefficient',b[1],-.00007,.00002)
 z=arr(29,'DZ');t=arr(29,'DT');y=arr(29,'DY');b,r,X=ols(y,t,z);check('M29','adjusted education effect',b[1],-.30,.015)
 check('M29','DID',(1.9-2.4)-(1.8-2),-.3,1e-12)
 xs=arr(30,'XS')[:5];sd=20/np.sqrt(5);check('M30','posterior mean and P(mu>=550)',[xs.mean(),stats.norm.sf(550,xs.mean(),sd)],[555.4,.727],.0006)
 dh=arr(31,'DH');posterior=json.loads((ROOT/'data/visual_stage2/m31_summary.json').read_text())
 check('M31','regenerated histogram contains every retained draw',dh.sum(),posterior['retained_count'],0)
 edges=np.array(posterior['delta']['edges']);centers=(edges[:-1]+edges[1:])/2
 check('M31','grouped posterior mean approximation',np.average(centers,weights=dh),posterior['diagnostics']['delta']['mean'],.05)
 dx=arr(32,'DX');ev=np.linalg.eigvalsh(np.corrcoef(dx,rowvar=False))[::-1];check('M32','first two eigenvalues and explained fraction',[ev[0],ev[1],sum(ev[:2])/5],[2.657,1.758,.883],.003)
 cp=arr(33,'CP');check('M33','population denominator SD for standardization',cp.std(axis=0),[1.130,9.777],.001)
 check('M34','sensitivity, specificity, PPV, accuracy',[32/40,144/160,32/48,176/200],[.8,.9,2/3,.88],1e-12)
 check('M34','MSE, RMSE, MAE',[np.mean(np.array([2,-3,-5,5,0])**2),np.sqrt(12.6),3],[12.6,3.549648,3],1e-6)
 check('M35','Newton cooling at 48 hours',25+575*np.exp(-.04*48),109.3,.05)
 def sir(t,y):
  S,I,R=y;rate=.34*S*I/1000;return [-rate,rate-.2*I,.2*I]
 sol=integrate.solve_ivp(sir,[0,500],[999,1,0],rtol=1e-10,atol=1e-10,dense_output=True)
 grid=sol.sol(np.arange(501));check('M36','SIR peak and final cumulative',[max(grid[1]),1000-grid[0,-1]],[100,692],.6)
 q=arr(37,'MQ');st=np.linalg.lstsq(np.vstack([q.T-np.eye(3),np.ones(3)]),[0,0,0,1],rcond=None)[0]
 check('M37','two-day failure probability and stationary vector',[(q@q)[0,2],*st],[.032,.846,.116,.038],.0006)
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2));print(len(results),'independent checks; M31 regenerated histogram count verified')
if __name__=='__main__':main()
