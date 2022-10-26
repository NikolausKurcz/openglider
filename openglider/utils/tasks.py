from __future__ import annotations
from ast import Call

from typing import Any, Callable, Iterator, List, Optional, Type
import functools
import asyncio
import logging
import time
import sys

logger = logging.getLogger(__name__)


async def execute_sync(func: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:
    return func(*args, **kwargs)

class Task:
    running = False
    finished = False
    failed = False

    parent: Optional[Task] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    execute: Callable[[Callable[[], Any]], Any]

    def __init__(self, name: str=None) -> None:
        self.execute = execute_sync
        self.name = name
    
    def get_name(self) -> str:
        name = self.__class__.__name__
        if self.name:
            name += f" {self.name}"
        
        return name
    
    def runtime(self) -> str:
        if self.start_time is None:
            return "--"
        
        if self.end_time is None:
            duration = time.time() - self.start_time
        else:
            duration = self.end_time - self.start_time
        
        return time.strftime("%H:%M:%S", time.gmtime(duration))
    
    @property
    def is_ready(self) -> bool:
        if self.parent is not None:
            if self.parent.failed:
                self.failed = True
                return False
            
            if not self.parent.finished:
                return False
        
        return True

    async def _run(self, execute: Callable[[Callable[[], Any]], Any]=None) -> Any:
        if execute is not None:
            self.execute = execute

        if self.finished:
            return

        self.running = True
        self.start_time = time.time()
        try:
            result = await self.run()
        except Exception as e:
            self.failed = True
            self.running = False
            raise e
        finally:
            self.running = False
            self.end_time = time.time()

        self.finished = True
        return result
    
    async def stop(self) -> None:
        self.running = False
        self.failed = True

    async def run(self) -> Any:
        return


class TaskQueue:
    tasks: List[Task]
    running = False
    exception_hook: Callable | None = None

    def __init__(self, execute_function: Callable[[Any], Any]=None):
        self.tasks = []

        if execute_function is None:
            execute_function = asyncio.create_task
            
        self.execute = execute_function
        asyncio.create_task(self.process())

    def add(self, task: Task) -> None:
        self.tasks.append(task)
    
    def is_busy(self) -> bool:
        for task in self.tasks:
            if task.running:
                return True
        
        return False
    
    async def quit(self) -> None:
        for task in self.tasks:
            if task.running:
                await task.stop()
    
    async def process(self) -> None:
        self.running = True

        while self.running:
            for task in self.tasks:
                if task.running:
                    raise Exception(f"running task in queue! {task}")

            for task in self.tasks:
                if not any([task.finished, task.running, task.failed]):
                    if task.is_ready:
                        try:
                            await task._run(self.execute)
                        except Exception as e:
                            if self.exception_hook:
                                self.exception_hook(*sys.exc_info())
                            else:
                                logger.error("fuck")
                                logger.error(e)

            
            await asyncio.sleep(1)
        

        
