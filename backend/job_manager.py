from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Any
from .config import settings
from .pipeline import Pipeline, ProductionBlocked

@dataclass
class JobState:
    job_id:str; status:str="queued"; progress:int=0; message:str="Na fila"; result:dict[str,Any]|None=None; error:dict[str,Any]|None=None
    def to_dict(self)->dict[str,Any]: return {"job_id":self.job_id,"status":self.status,"progress":self.progress,"message":self.message,"result":self.result,"error":self.error}

class JobManager:
    def __init__(self,pipeline:Pipeline): self.pipeline=pipeline; self.pool=ThreadPoolExecutor(max_workers=max(1,settings.worker_count),thread_name_prefix="fechaprint"); self.jobs={}; self.lock=Lock()
    def create(self,job_id:str,source,**kwargs)->JobState:
        state=JobState(job_id=job_id)
        with self.lock: self.jobs[job_id]=state
        self.pool.submit(self._run,state,source,kwargs); return state
    def get(self,job_id:str)->JobState|None:
        with self.lock: return self.jobs.get(job_id)
    def _update(self,state:JobState,progress:int,message:str):
        with self.lock: state.status="processing"; state.progress=max(0,min(100,int(progress))); state.message=message
    def _run(self,state:JobState,source,kwargs):
        try:
            result=self.pipeline.process(source,job_id=state.job_id,progress=lambda p,m:self._update(state,p,m),**kwargs)
            with self.lock: state.status="completed"; state.progress=100; state.message="Arquivo pronto"; state.result=result
        except ProductionBlocked as exc:
            with self.lock: state.status="blocked"; state.message=str(exc); state.error=exc.payload()
        except Exception as exc:
            with self.lock: state.status="failed"; state.message="Falha no processamento"; state.error={"code":"processing_failed","message":str(exc)}
