
from designkit.behavioral.typing import Assertion
from pydantic import BaseModel
from datetime import date
from typing import Any
import math
from datetime import datetime

acertacion1 = Assertion( 255.6 )
acertacion2 = Assertion( None )

print('A1: Deberia ser Entero o Flotante --', acertacion1.should_be(int, float))
print('A2: Deberia ser Entero o Flotante --', acertacion2.should_be(int, float))




class YFinanceDividend(BaseModel):
    date: date
    amount: float

class YFinanceSplit(BaseModel):
    date: date
    ratio: float | str

def _scalar(value: Any) -> int | float | str | None:
    if value is None:
        return None
    if hasattr(value, 'item'):
        value = value.item()
    
    match value:
        case float() if math.isnan(value):
            return None
        case datetime() | date():
            return value.isoformat()
        case int() | float() | str():
            return value
        case bool():
            return int(value) 

    return str(value)

def _as_date(value: Any) -> date:
    if Assertion(value).should_have('to_pydatetime'):
        value = value.to_pydatetime()

    match value:
        case datetime():
            return value.date()

        case date():
            return value

    return date.fromisoformat(str(value)[:10])

def _action_point(index: Any, row: Any) -> tuple[YFinanceDividend | None, YFinanceSplit | None]:
    dividend: int | float | None = _scalar(row.get('Dividends'))
    split: int | float | str | None = _scalar(row.get('Stock Splits'))
    print('Se encontro un dividend:', dividend)
    print('Se encontro un split:', split)

    dividend_obj: YFinanceDividend | None = None
    split_obj: YFinanceSplit | None = None

    assertion: Assertion = Assertion(dividend)
    if assertion.should_be(int, float) and assertion.should_comply(lambda x: x != 0):
        print(f'Según la acertación fue verdadera para el dividendo: {dividend}')
        dividend_obj = YFinanceDividend(date=_as_date(index), amount=float(dividend))
    if Assertion(split).should_be(int, float, str) and split not in (0, '0', ''):
        print(f'Según la acertación fue verdadera para el split: {split}')
        split_obj = YFinanceSplit(date=_as_date(index), ratio=split)
    return dividend_obj, split_obj

_action_point(datetime.now(), {'Dividends': 1.5, 'Stock Splits': '2:1'})

