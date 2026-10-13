
from designkit.behavioral.typing import Assertion
from abc import ABC, abstractmethod

from finance.services.ml.models import PredictionResult
from finance.services.ml.exceptions import InvalidMiddlewareError



# ================================================== #
# TYPE ALIASES                                    #
# ================================================== #

type CurrentShares = int
type CurrentPrice = float
type Prediction = tuple[PredictionResult, CurrentShares, CurrentPrice]



# ================================================== #
# ABSTRACT BASE CLASSES                           #
# ================================================== #

class Middleware(ABC):
    @abstractmethod
    def process(self, *predictions: Prediction) -> dict[str, int]:
        pass



# ================================================== #
# INVOKER CLASS                                   #
# ================================================== #

class MiddlewareInvoker:
    @staticmethod
    def execute(middleware: Middleware) -> dict[str, int]:
        Assertion(middleware).must_be(Middleware, custom_expt=InvalidMiddlewareError(middleware))
        return middleware.process()
