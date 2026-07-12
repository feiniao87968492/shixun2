from __future__ import annotations

import math
import sys
import importlib.util
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

_PREPROCESSING_SPEC = importlib.util.spec_from_file_location(
    "q2_local_preprocessing",
    SCRIPT_DIR / "preprocessing.py",
)
if _PREPROCESSING_SPEC is None or _PREPROCESSING_SPEC.loader is None:
    raise ImportError("Unable to load q2 preprocessing module")
_PREPROCESSING = importlib.util.module_from_spec(_PREPROCESSING_SPEC)
_PREPROCESSING_SPEC.loader.exec_module(_PREPROCESSING)

m_to_yd = _PREPROCESSING.m_to_yd
mph_to_mps = _PREPROCESSING.mph_to_mps
rpm_to_rad_s = _PREPROCESSING.rpm_to_rad_s
yd_to_m = _PREPROCESSING.yd_to_m


class PhysicalConstants:
    def __init__(
        self,
        *,
        mass_kg: float,
        radius_m: float,
        air_density_kg_m3: float,
        gravity_m_s2: float,
        initial_height_m: float,
        source: str,
    ) -> None:
        self.mass_kg = float(mass_kg)
        self.radius_m = float(radius_m)
        self.air_density_kg_m3 = float(air_density_kg_m3)
        self.gravity_m_s2 = float(gravity_m_s2)
        self.initial_height_m = float(initial_height_m)
        self.source = source

    @classmethod
    def from_config(cls, physics: dict[str, Any]) -> "PhysicalConstants":
        radius = physics.get("radius_m")
        if radius is None:
            radius = float(physics["diameter_m"]) / 2.0
        return cls(
            mass_kg=float(physics["mass_kg"]),
            radius_m=float(radius),
            air_density_kg_m3=float(physics["air_density_kg_m3"]),
            gravity_m_s2=float(physics["gravity_m_s2"]),
            initial_height_m=float(physics["initial_height_m"]),
            source=str(physics["source"]),
        )

    @property
    def area_m2(self) -> float:
        return math.pi * self.radius_m**2


def initial_velocity_mps(row: pd.Series) -> np.ndarray:
    speed = mph_to_mps(float(row["ball_speed_mph"]))
    theta = math.radians(float(row["launch_angle_deg"]))
    phi = math.radians(float(row["launch_direction_deg"]))
    return np.asarray(
        [
            speed * math.cos(theta) * math.cos(phi),
            speed * math.cos(theta) * math.sin(phi),
            speed * math.sin(theta),
        ],
        dtype=float,
    )


def vacuum_analytic(row: pd.Series, constants: PhysicalConstants) -> dict[str, float]:
    vx, vy, vz = initial_velocity_mps(row)
    g = constants.gravity_m_s2
    z0 = constants.initial_height_m
    flight_time = (vz + math.sqrt(vz**2 + 2.0 * g * z0)) / g
    x_land = vx * flight_time
    y_land = vy * flight_time
    apex = z0 + vz**2 / (2.0 * g)
    carry_m = math.sqrt(x_land**2 + y_land**2)
    return {
        "predicted_carry_yd": m_to_yd(carry_m),
        "predicted_x_carry_yd": m_to_yd(x_land),
        "predicted_lateral_yd": m_to_yd(y_land),
        "predicted_apex_yd": m_to_yd(apex),
        "flight_time_s": float(flight_time),
    }


def _rhs_factory(model: str, constants: PhysicalConstants, *, cd: float) -> Any:
    drag_factor = 0.5 * constants.air_density_kg_m3 * constants.area_m2 * cd / constants.mass_kg

    def rhs(_t: float, state: np.ndarray) -> np.ndarray:
        velocity = state[3:6]
        speed = float(np.linalg.norm(velocity))
        acceleration = np.asarray([0.0, 0.0, -constants.gravity_m_s2], dtype=float)
        if model == "drag" and speed > 1e-12:
            acceleration -= drag_factor * speed * velocity
        return np.asarray([velocity[0], velocity[1], velocity[2], *acceleration], dtype=float)

    return rhs


def _ground_event(_t: float, state: np.ndarray) -> float:
    return float(state[2])


_ground_event.terminal = True  # type: ignore[attr-defined]
_ground_event.direction = -1  # type: ignore[attr-defined]


def simulate_shot(
    row: pd.Series,
    *,
    model: str,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    cd: float = 0.0,
    keep_trajectory: bool = False,
) -> tuple[dict[str, Any], pd.DataFrame]:
    if model not in {"vacuum", "drag"}:
        raise ValueError(f"q2 first-stage ODE supports vacuum/drag, got {model}")
    initial_state = np.asarray(
        [0.0, 0.0, constants.initial_height_m, *initial_velocity_mps(row)],
        dtype=float,
    )
    sol = solve_ivp(
        _rhs_factory(model, constants, cd=cd),
        (0.0, 12.0),
        initial_state,
        method=str(solver.get("method", "DOP853")),
        rtol=float(solver.get("rtol", 1e-7)),
        atol=float(solver.get("atol", 1e-9)),
        max_step=float(solver.get("max_step", 0.02)),
        events=_ground_event,
    )
    status = "success" if sol.success and len(sol.t_events[0]) > 0 else "failed"
    if status == "success":
        event_time = float(sol.t_events[0][0])
        event_state = sol.y_events[0][0]
        states = sol.y.T
        times = sol.t
        if not np.isclose(times[-1], event_time):
            times = np.append(times, event_time)
            states = np.vstack([states, event_state])
    else:
        times = sol.t
        states = sol.y.T
        event_time = float(times[-1]) if len(times) else np.nan
        event_state = states[-1] if len(states) else np.full(6, np.nan)

    x_land, y_land, z_land = event_state[:3]
    z_values = states[:, 2] if len(states) else np.asarray([np.nan])
    output = {
        "model": model,
        "integration_status": status,
        "predicted_carry_yd": m_to_yd(math.sqrt(float(x_land) ** 2 + float(y_land) ** 2)),
        "predicted_x_carry_yd": m_to_yd(float(x_land)),
        "predicted_lateral_yd": m_to_yd(float(y_land)),
        "predicted_apex_yd": m_to_yd(float(np.nanmax(z_values))),
        "flight_time_s": event_time,
        "solver_success": bool(sol.success),
        "solver_message": str(sol.message),
    }
    if keep_trajectory:
        trajectory = pd.DataFrame(
            {
                "time_s": times,
                "x_m": states[:, 0],
                "y_m": states[:, 1],
                "z_m": states[:, 2],
                "x_yd": [m_to_yd(value) for value in states[:, 0]],
                "y_yd": [m_to_yd(value) for value in states[:, 1]],
                "z_yd": [m_to_yd(value) for value in states[:, 2]],
            }
        )
    else:
        trajectory = pd.DataFrame({"time_s": [output["flight_time_s"]]})
    return output, trajectory


def calibrate_drag_cd(
    calibration_records: pd.DataFrame,
    *,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    bounds: tuple[float, float],
    grid_size: int,
) -> tuple[float, pd.DataFrame]:
    cd_values = np.linspace(bounds[0], bounds[1], int(grid_size))
    carry_scale = float(calibration_records["carry_distance_yd"].std(ddof=1))
    apex_scale = float(calibration_records["apex_height_yd"].std(ddof=1))
    rows = []
    for cd in cd_values:
        losses = []
        failures = 0
        for _, row in calibration_records.iterrows():
            pred, _ = simulate_shot(row, model="drag", constants=constants, solver=solver, cd=float(cd))
            if pred["integration_status"] != "success":
                failures += 1
                continue
            carry_error = (pred["predicted_carry_yd"] - float(row["carry_distance_yd"])) / carry_scale
            apex_error = (pred["predicted_apex_yd"] - float(row["apex_height_yd"])) / apex_scale
            losses.append(carry_error**2 + apex_error**2)
        objective = float(np.mean(losses)) if losses else np.inf
        rows.append(
            {
                "cd": float(cd),
                "objective": objective,
                "calibration_n": int(len(calibration_records)),
                "failed_count": int(failures),
            }
        )
    surface = pd.DataFrame(rows)
    best = surface.sort_values(["objective", "cd"]).iloc[0]
    return float(best["cd"]), surface


def evaluate_ode_models(
    test: pd.DataFrame,
    *,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    cd: float,
) -> dict[str, pd.DataFrame]:
    prediction_rows = []
    failure_rows = []
    for model in ["vacuum", "drag"]:
        failed_ids = []
        for _, row in test.iterrows():
            pred, _ = simulate_shot(row, model=model, constants=constants, solver=solver, cd=cd)
            if pred["integration_status"] != "success":
                failed_ids.append(int(row["record_id"]))
            prediction_rows.append(
                {
                    "record_id": int(row["record_id"]),
                    "model": model,
                    "actual_carry_yd": float(row["carry_distance_yd"]),
                    "predicted_carry_yd": pred["predicted_carry_yd"],
                    "actual_apex_yd": float(row["apex_height_yd"]),
                    "predicted_apex_yd": pred["predicted_apex_yd"],
                    "actual_lateral_yd": float(row["lateral_offset_yd"]),
                    "predicted_lateral_yd": pred["predicted_lateral_yd"],
                    "flight_time_s": pred["flight_time_s"],
                    "integration_status": pred["integration_status"],
                }
            )
        failure_rows.append(
            {
                "model": model,
                "failed_count": int(len(failed_ids)),
                "test_n": int(len(test)),
                "failed_record_ids": ";".join(map(str, failed_ids)),
            }
        )
    predictions = pd.DataFrame(prediction_rows)
    metrics = ode_metrics(predictions)
    comparison = metrics[
        ["model", "carry_rmse", "carry_mape", "apex_rmse", "apex_mape", "lateral_mae", "flight_failure_rate"]
    ].copy()
    return {
        "predictions": predictions,
        "metrics": metrics,
        "comparison": comparison,
        "failures": pd.DataFrame(failure_rows),
    }


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(math.sqrt(np.mean((predicted - actual) ** 2)))


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = np.abs(actual) > 1e-12
    return float(np.mean(np.abs((predicted[mask] - actual[mask]) / actual[mask])) * 100.0)


def ode_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, subset in predictions.groupby("model"):
        ok = subset[subset["integration_status"] == "success"]
        carry_actual = ok["actual_carry_yd"].to_numpy(dtype=float)
        carry_pred = ok["predicted_carry_yd"].to_numpy(dtype=float)
        apex_actual = ok["actual_apex_yd"].to_numpy(dtype=float)
        apex_pred = ok["predicted_apex_yd"].to_numpy(dtype=float)
        lateral_actual = ok["actual_lateral_yd"].to_numpy(dtype=float)
        lateral_pred = ok["predicted_lateral_yd"].to_numpy(dtype=float)
        rows.append(
            {
                "model": model,
                "test_n": int(len(subset)),
                "success_n": int(len(ok)),
                "carry_rmse": _rmse(carry_actual, carry_pred),
                "carry_mape": _mape(carry_actual, carry_pred),
                "apex_rmse": _rmse(apex_actual, apex_pred),
                "apex_mape": _mape(apex_actual, apex_pred),
                "lateral_mae": float(np.mean(np.abs(lateral_pred - lateral_actual))),
                "flight_failure_rate": float(1.0 - len(ok) / len(subset)),
            }
        )
    return pd.DataFrame(rows).sort_values("model").reset_index(drop=True)


def validation_checks(
    sample_row: pd.Series,
    *,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    cd: float,
) -> pd.DataFrame:
    vacuum_numeric, _ = simulate_shot(sample_row, model="vacuum", constants=constants, solver=solver)
    vacuum_exact = vacuum_analytic(sample_row, constants)
    max_error = max(
        abs(vacuum_numeric["predicted_carry_yd"] - vacuum_exact["predicted_carry_yd"]),
        abs(vacuum_numeric["predicted_apex_yd"] - vacuum_exact["predicted_apex_yd"]),
        abs(vacuum_numeric["flight_time_s"] - vacuum_exact["flight_time_s"]),
    )
    drag_numeric, _ = simulate_shot(sample_row, model="drag", constants=constants, solver=solver, cd=cd)
    rows = [
        {"check": "mph_to_mps", "passed": abs(mph_to_mps(1.0) - 0.44704) < 1e-12, "value": mph_to_mps(1.0)},
        {
            "check": "rpm_to_rad_s",
            "passed": abs(rpm_to_rad_s(60.0) - 2.0 * math.pi) < 1e-12,
            "value": rpm_to_rad_s(60.0),
        },
        {"check": "yd_to_m", "passed": abs(yd_to_m(1.0) - 0.9144) < 1e-12, "value": yd_to_m(1.0)},
        {
            "check": "vacuum_numeric_matches_analytic",
            "passed": max_error < 1e-3,
            "value": float(max_error),
        },
        {
            "check": "drag_model_reduces_vacuum_carry",
            "passed": drag_numeric["predicted_carry_yd"] < vacuum_numeric["predicted_carry_yd"],
            "value": float(vacuum_numeric["predicted_carry_yd"] - drag_numeric["predicted_carry_yd"]),
        },
        {
            "check": "ground_event_success",
            "passed": vacuum_numeric["integration_status"] == "success" and drag_numeric["integration_status"] == "success",
            "value": 1.0,
        },
    ]
    return pd.DataFrame(rows)
