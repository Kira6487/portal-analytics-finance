from __future__ import annotations

from abc import ABC, abstractmethod
import warnings

import numpy as np
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.holtwinters import ExponentialSmoothing


class ForecastModel(ABC):
    name: str

    @abstractmethod
    def fit(self, series: list[float]) -> "ForecastModel":
        raise NotImplementedError

    @abstractmethod
    def predict(self, periods: int) -> list[float]:
        raise NotImplementedError


class NaiveLastValue(ForecastModel):
    name = "naive_last_value"

    def fit(self, series: list[float]) -> "NaiveLastValue":
        if not series:
            raise ValueError("La serie está vacía.")
        self.value = float(series[-1])
        return self

    def predict(self, periods: int) -> list[float]:
        return [self.value] * periods


class SeasonalNaive12(ForecastModel):
    name = "seasonal_naive_12"

    def fit(self, series: list[float]) -> "SeasonalNaive12":
        if len(series) < 12:
            raise ValueError("Seasonal Naive requiere al menos 12 meses.")
        self.series = [float(value) for value in series]
        return self

    def predict(self, periods: int) -> list[float]:
        values = list(self.series)
        forecasts = []
        for _ in range(periods):
            forecast = values[-12]
            forecasts.append(forecast)
            values.append(forecast)
        return forecasts


class MovingAverage(ForecastModel):
    def __init__(self, window: int):
        self.window = window
        self.name = f"moving_average_{window}"

    def fit(self, series: list[float]) -> "MovingAverage":
        if len(series) < self.window:
            raise ValueError(f"Media móvil {self.window} requiere {self.window} meses.")
        self.series = [float(value) for value in series]
        return self

    def predict(self, periods: int) -> list[float]:
        values = list(self.series)
        forecasts = []
        for _ in range(periods):
            forecast = float(np.mean(values[-self.window:]))
            forecasts.append(forecast)
            values.append(forecast)
        return forecasts


class HoltWintersModel(ForecastModel):
    name = "holt_winters"

    def fit(self, series: list[float]) -> "HoltWintersModel":
        if len(series) < 24:
            raise ValueError("Holt-Winters estacional requiere al menos 24 meses.")
        values = np.asarray(series, dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("La serie contiene valores no finitos.")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.result = ExponentialSmoothing(
                values,
                trend="add",
                seasonal="add",
                seasonal_periods=12,
                initialization_method="estimated",
            ).fit(optimized=True, remove_bias=True)
        return self

    def predict(self, periods: int) -> list[float]:
        return [float(value) for value in self.result.forecast(periods)]


class CalendarLinearRegression(ForecastModel):
    name = "calendar_linear_regression"

    def fit(self, series: list[float]) -> "CalendarLinearRegression":
        if len(series) < 12:
            raise ValueError("Regresión calendario requiere al menos 12 meses.")
        self.length = len(series)
        x = self._features(range(self.length))
        self.model = LinearRegression().fit(x, np.asarray(series, dtype=float))
        return self

    @staticmethod
    def _features(indices) -> np.ndarray:
        rows = []
        for index in indices:
            month = index % 12
            quarter = month // 3
            dummies = [1.0 if month == candidate else 0.0 for candidate in range(1, 12)]
            rows.append([float(index), float(month + 1), float(quarter + 1), *dummies])
        return np.asarray(rows, dtype=float)

    def predict(self, periods: int) -> list[float]:
        x = self._features(range(self.length, self.length + periods))
        return [float(value) for value in self.model.predict(x)]


def available_models() -> list[ForecastModel]:
    return [
        NaiveLastValue(),
        SeasonalNaive12(),
        MovingAverage(3),
        MovingAverage(6),
        HoltWintersModel(),
        CalendarLinearRegression(),
    ]


def create_model(name: str) -> ForecastModel:
    models = {model.name: model for model in available_models()}
    if name not in models:
        raise ValueError(f"Modelo desconocido: {name}")
    return models[name]
