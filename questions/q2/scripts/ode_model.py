from __future__ import annotations

import math
import sys
import importlib.util
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import minimize

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

ODE_MODELS = ["vacuum", "drag", "constant_lift", "spin_factor_lift"]
CARRY_DEFINITIONS = {"forward_x", "radial"}


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
        initial_height_type: str = "numerical_convention",
    ) -> None:
        self.mass_kg = float(mass_kg)
        self.radius_m = float(radius_m)
        self.air_density_kg_m3 = float(air_density_kg_m3)
        self.gravity_m_s2 = float(gravity_m_s2)
        self.initial_height_m = float(initial_height_m)
        self.initial_height_type = str(initial_height_type)
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
            initial_height_type=str(physics.get("initial_height_type", "numerical_convention")),
            source=str(physics["source"]),
        )

    @property
    def area_m2(self) -> float:
        return math.pi * self.radius_m**2

    def with_initial_height(self, initial_height_m: float) -> "PhysicalConstants":
        return PhysicalConstants(
            mass_kg=self.mass_kg,
            radius_m=self.radius_m,
            air_density_kg_m3=self.air_density_kg_m3,
            gravity_m_s2=self.gravity_m_s2,
            initial_height_m=float(initial_height_m),
            initial_height_type=self.initial_height_type,
            source=self.source,
        )


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


def spin_components_rad_s(row: pd.Series, *, side_sign: int = 1) -> tuple[float, float]:
    spin_rate = rpm_to_rad_s(float(row["spin_rate_rpm"]))
    axis = math.radians(float(row["spin_axis_deg"]))
    backspin = spin_rate * math.cos(axis)
    sidespin = float(side_sign) * spin_rate * math.sin(axis)
    return float(backspin), float(sidespin)


def spin_vector_rad_s(row: pd.Series, *, side_sign: int = 1) -> np.ndarray:
    """Construct global spin vector. Positive backspin points along local +left axis."""
    phi = math.radians(float(row["launch_direction_deg"]))
    e_lateral = np.asarray([-math.sin(phi), math.cos(phi), 0.0], dtype=float)
    e_vertical = np.asarray([0.0, 0.0, 1.0], dtype=float)
    backspin, sidespin = spin_components_rad_s(row, side_sign=side_sign)
    return backspin * e_lateral + sidespin * e_vertical


def select_predicted_carry(prediction: dict[str, float], carry_definition: str) -> float:
    if carry_definition == "forward_x":
        return float(prediction["predicted_x_carry_yd"])
    if carry_definition == "radial":
        return float(prediction["predicted_radial_carry_yd"])
    raise ValueError(f"Unsupported carry_definition: {carry_definition}")


def vacuum_analytic(
    row: pd.Series,
    constants: PhysicalConstants,
    *,
    carry_definition: str,
) -> dict[str, float]:
    vx, vy, vz = initial_velocity_mps(row)
    g = constants.gravity_m_s2
    z0 = constants.initial_height_m
    flight_time = (vz + math.sqrt(vz**2 + 2.0 * g * z0)) / g
    x_land = vx * flight_time
    y_land = vy * flight_time
    apex = z0 + vz**2 / (2.0 * g)
    output = {
        "predicted_radial_carry_yd": m_to_yd(math.sqrt(x_land**2 + y_land**2)),
        "predicted_x_carry_yd": m_to_yd(x_land),
        "predicted_forward_carry_yd": m_to_yd(x_land),
        "predicted_lateral_yd": m_to_yd(y_land),
        "predicted_apex_yd": m_to_yd(apex),
        "flight_time_s": float(flight_time),
        "carry_definition": carry_definition,
    }
    output["predicted_carry_yd"] = select_predicted_carry(output, carry_definition)
    return output


def _rhs_factory(
    model: str,
    row: pd.Series,
    constants: PhysicalConstants,
    *,
    cd: float,
    cl: float,
    lift_scale: float,
    side_sign: int,
    wind_mps: tuple[float, float, float],
    spin_decay_s: float | None,
) -> Any:
    drag_factor = 0.5 * constants.air_density_kg_m3 * constants.area_m2 * cd / constants.mass_kg
    lift_factor = 0.5 * constants.air_density_kg_m3 * constants.area_m2 / constants.mass_kg
    wind = np.asarray(wind_mps, dtype=float)
    omega0 = spin_vector_rad_s(row, side_sign=side_sign)

    def rhs(t: float, state: np.ndarray) -> np.ndarray:
        velocity = state[3:6]
        relative_velocity = velocity - wind
        speed = float(np.linalg.norm(relative_velocity))
        acceleration = np.asarray([0.0, 0.0, -constants.gravity_m_s2], dtype=float)
        if model in {"drag", "constant_lift", "spin_factor_lift"} and speed > 1e-12:
            acceleration -= drag_factor * speed * relative_velocity
        if model in {"constant_lift", "spin_factor_lift"} and speed > 1e-12:
            omega = omega0
            if spin_decay_s is not None and spin_decay_s > 0:
                omega = omega0 * math.exp(-float(t) / float(spin_decay_s))
            cross = np.cross(relative_velocity, omega)
            cross_norm = float(np.linalg.norm(cross))
            omega_norm = float(np.linalg.norm(omega))
            if cross_norm > 1e-12 and omega_norm > 1e-12:
                direction = cross / cross_norm
                if model == "constant_lift":
                    lift_coefficient = float(cl)
                else:
                    spin_factor = constants.radius_m * omega_norm / max(speed, 1e-12)
                    lift_coefficient = float(lift_scale) * spin_factor
                acceleration += lift_factor * lift_coefficient * speed**2 * direction
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
    carry_definition: str,
    cd: float = 0.0,
    cl: float = 0.0,
    lift_scale: float = 0.0,
    side_sign: int = 1,
    wind_mps: tuple[float, float, float] = (0.0, 0.0, 0.0),
    spin_decay_s: float | None = None,
    keep_trajectory: bool = False,
) -> tuple[dict[str, Any], pd.DataFrame]:
    if model not in set(ODE_MODELS):
        raise ValueError(f"q2 ODE supports {ODE_MODELS}, got {model}")
    if carry_definition not in CARRY_DEFINITIONS:
        raise ValueError(f"Unsupported carry_definition: {carry_definition}")
    initial_state = np.asarray(
        [0.0, 0.0, constants.initial_height_m, *initial_velocity_mps(row)],
        dtype=float,
    )
    sol = solve_ivp(
        _rhs_factory(
            model,
            row,
            constants,
            cd=float(cd),
            cl=float(cl),
            lift_scale=float(lift_scale),
            side_sign=int(side_sign),
            wind_mps=wind_mps,
            spin_decay_s=spin_decay_s,
        ),
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

    x_land, y_land, _z_land = event_state[:3]
    z_values = states[:, 2] if len(states) else np.asarray([np.nan])
    output = {
        "model": model,
        "integration_status": status,
        "predicted_radial_carry_yd": m_to_yd(math.sqrt(float(x_land) ** 2 + float(y_land) ** 2)),
        "predicted_x_carry_yd": m_to_yd(float(x_land)),
        "predicted_forward_carry_yd": m_to_yd(float(x_land)),
        "predicted_lateral_yd": m_to_yd(float(y_land)),
        "predicted_apex_yd": m_to_yd(float(np.nanmax(z_values))),
        "flight_time_s": event_time,
        "carry_definition": carry_definition,
        "solver_success": bool(sol.success),
        "solver_message": str(sol.message),
        "cd": float(cd),
        "cl": float(cl),
        "lift_scale": float(lift_scale),
    }
    output["predicted_carry_yd"] = select_predicted_carry(output, carry_definition)
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


def _scales(records: pd.DataFrame) -> tuple[float, float, float]:
    carry_scale = float(records["carry_distance_yd"].std(ddof=1)) or 1.0
    apex_scale = float(records["apex_height_yd"].std(ddof=1)) or 1.0
    lateral_scale = float(records.get("lateral_offset_yd", pd.Series([1.0])).std(ddof=1)) or 1.0
    return carry_scale, apex_scale, lateral_scale


def _objective(
    records: pd.DataFrame,
    *,
    model: str,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    carry_definition: str,
    failure_penalty: float,
    cd: float,
    cl: float = 0.0,
    lift_scale: float = 0.0,
    side_sign: int = 1,
    lateral_weight: float = 0.0,
) -> tuple[float, int]:
    carry_scale, apex_scale, lateral_scale = _scales(records)
    losses = []
    failures = 0
    for _, row in records.iterrows():
        pred, _ = simulate_shot(
            row,
            model=model,
            constants=constants,
            solver=solver,
            cd=cd,
            cl=cl,
            lift_scale=lift_scale,
            side_sign=side_sign,
            carry_definition=carry_definition,
        )
        if pred["integration_status"] != "success":
            failures += 1
            continue
        carry_error = (pred["predicted_carry_yd"] - float(row["carry_distance_yd"])) / carry_scale
        apex_error = (pred["predicted_apex_yd"] - float(row["apex_height_yd"])) / apex_scale
        lateral_error = 0.0
        if "lateral_offset_yd" in row:
            lateral_error = (pred["predicted_lateral_yd"] - float(row["lateral_offset_yd"])) / lateral_scale
        losses.append(carry_error**2 + apex_error**2 + lateral_weight * lateral_error**2)
    failure_fraction = float(failures) / float(len(records)) if len(records) else 1.0
    mean_loss = float(np.mean(losses)) if losses else float(failure_penalty)
    objective = mean_loss + float(failure_penalty) * failure_fraction
    return objective, failures


def calibrate_drag_cd(
    calibration_records: pd.DataFrame,
    *,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    bounds: tuple[float, float],
    grid_size: int,
    local_optimization: dict[str, Any],
    carry_definition: str,
    failure_penalty: float,
    full_train_records: pd.DataFrame | None = None,
    return_runs: bool = False,
) -> tuple[float, pd.DataFrame] | tuple[float, pd.DataFrame, pd.DataFrame]:
    cd_values = np.linspace(bounds[0], bounds[1], int(grid_size))
    rows = []
    for cd in cd_values:
        objective, failures = _objective(
            calibration_records,
            model="drag",
            constants=constants,
            solver=solver,
            cd=float(cd),
            carry_definition=carry_definition,
            failure_penalty=failure_penalty,
        )
        rows.append(
            {
                "model": "drag",
                "carry_definition": carry_definition,
                "cd": float(cd),
                "cl": np.nan,
                "lift_scale": np.nan,
                "objective": objective,
                "calibration_n": int(len(calibration_records)),
                "failed_count": int(failures),
                "coarse_grid_rank": np.nan,
            }
        )
    surface = pd.DataFrame(rows)
    surface = surface.sort_values(["objective", "cd"]).reset_index(drop=True)
    surface["coarse_grid_rank"] = np.arange(1, len(surface) + 1)

    starts = [
        (
            f"grid_rank_{int(row.coarse_grid_rank)}",
            float(row.cd),
            int(row.coarse_grid_rank),
        )
        for row in surface.head(min(3, len(surface))).itertuples(index=False)
    ]
    starts.append(("midpoint", float((bounds[0] + bounds[1]) / 2.0), 0))
    objective_records = full_train_records if full_train_records is not None else calibration_records
    run_rows = []
    options = {
        "maxiter": int(local_optimization.get("maxiter", 40)),
        "maxfev": int(local_optimization.get("maxfev", 120)),
        "xtol": float(local_optimization.get("xtol", 1e-4)),
        "ftol": float(local_optimization.get("ftol", 1e-6)),
    }
    method = str(local_optimization.get("method", "Powell"))
    minimum_improvement = float(local_optimization.get("minimum_improvement", 1e-6))

    def local_objective(values: np.ndarray) -> float:
        objective, _failures = _objective(
            calibration_records,
            model="drag",
            constants=constants,
            solver=solver,
            cd=float(values[0]),
            carry_definition=carry_definition,
            failure_penalty=failure_penalty,
        )
        return float(objective)

    for start_label, initial_cd, coarse_rank in starts:
        initial_objective, initial_failures = _objective(
            calibration_records,
            model="drag",
            constants=constants,
            solver=solver,
            cd=float(initial_cd),
            carry_definition=carry_definition,
            failure_penalty=failure_penalty,
        )
        result = minimize(
            local_objective,
            x0=np.asarray([initial_cd], dtype=float),
            method=method,
            bounds=[bounds],
            options=options,
        )
        final_cd = float(np.clip(result.x[0], bounds[0], bounds[1]))
        objective, failures = _objective(
            calibration_records,
            model="drag",
            constants=constants,
            solver=solver,
            cd=final_cd,
            carry_definition=carry_definition,
            failure_penalty=failure_penalty,
        )
        termination_message = str(result.message)
        if objective > initial_objective + minimum_improvement:
            final_cd = float(initial_cd)
            objective = float(initial_objective)
            failures = int(initial_failures)
            termination_message = (
                f"{termination_message}; retained initial point because local result did not improve objective"
            )
        optimizer_success = bool(result.success)
        objective_finite = bool(np.isfinite(objective))
        accepted = optimizer_success and objective_finite and int(failures) == 0
        boundary_margin = min(final_cd - float(bounds[0]), float(bounds[1]) - final_cd)
        run_rows.append(
            {
                "model": "drag",
                "carry_definition": carry_definition,
                "start_label": start_label,
                "coarse_grid_rank": int(coarse_rank),
                "initial_cd": float(initial_cd),
                "final_cd": final_cd,
                "objective": float(objective),
                "initial_objective": float(initial_objective),
                "final_objective": float(objective),
                "objective_improvement": float(initial_objective - objective),
                "optimizer_success": optimizer_success,
                "objective_finite": objective_finite,
                "accepted": accepted,
                "success": optimizer_success,
                "termination_message": termination_message,
                "message": termination_message,
                "iterations": int(getattr(result, "nit", 0)),
                "function_evaluations": int(getattr(result, "nfev", 0)),
                "calibration_n": int(len(calibration_records)),
                "calibration_failed_count": int(failures),
                "failed_count": int(failures),
                "initial_failed_count": int(initial_failures),
                "boundary_margin": float(boundary_margin),
                "selected": False,
                "full_train_objective": np.nan,
                "full_train_failed_count": np.nan,
            }
        )

    runs = pd.DataFrame(run_rows)
    accepted_runs = runs[runs["accepted"].astype(bool)]
    if accepted_runs.empty:
        raise RuntimeError("drag calibration failed: no accepted local optimization run")
    best = accepted_runs.sort_values(
        ["final_objective", "boundary_margin", "final_cd"],
        ascending=[True, False, True],
    ).iloc[0]
    best_index = best.name
    best_cd = float(best["final_cd"])
    full_train_objective, full_train_failures = _objective(
        objective_records,
        model="drag",
        constants=constants,
        solver=solver,
        cd=best_cd,
        carry_definition=carry_definition,
        failure_penalty=failure_penalty,
    )
    runs.loc[best_index, "selected"] = True
    runs.loc[best_index, "full_train_objective"] = float(full_train_objective)
    runs.loc[best_index, "full_train_failed_count"] = int(full_train_failures)
    if return_runs:
        return best_cd, surface, runs
    return best_cd, surface


def calibrate_lift_parameters(
    calibration_records: pd.DataFrame,
    *,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    cd_bounds: tuple[float, float],
    lift_bounds: tuple[float, float],
    grid_size: int,
    model: str,
    side_sign: int,
    lateral_weight: float,
    local_optimization: dict[str, Any],
    carry_definition: str,
    failure_penalty: float,
    full_train_records: pd.DataFrame | None = None,
    return_runs: bool = False,
) -> tuple[dict[str, float], pd.DataFrame] | tuple[dict[str, float], pd.DataFrame, pd.DataFrame]:
    if model not in {"constant_lift", "spin_factor_lift"}:
        raise ValueError(f"Unsupported lift calibration model: {model}")
    cd_values = np.linspace(cd_bounds[0], cd_bounds[1], int(grid_size))
    lift_values = np.linspace(lift_bounds[0], lift_bounds[1], int(grid_size))
    rows = []
    for cd in cd_values:
        for lift_value in lift_values:
            cl = float(lift_value) if model == "constant_lift" else 0.0
            lift_scale = float(lift_value) if model == "spin_factor_lift" else 0.0
            objective, failures = _objective(
                calibration_records,
                model=model,
                constants=constants,
                solver=solver,
                cd=float(cd),
                cl=cl,
                lift_scale=lift_scale,
                side_sign=side_sign,
                lateral_weight=float(lateral_weight),
                carry_definition=carry_definition,
                failure_penalty=failure_penalty,
            )
            rows.append(
                {
                    "model": model,
                    "carry_definition": carry_definition,
                    "cd": float(cd),
                    "cl": cl if model == "constant_lift" else np.nan,
                    "lift_scale": lift_scale if model == "spin_factor_lift" else np.nan,
                    "objective": objective,
                    "calibration_n": int(len(calibration_records)),
                    "failed_count": int(failures),
                    "coarse_grid_rank": np.nan,
                }
            )
    surface = pd.DataFrame(rows)
    sort_cols = ["objective", "cd", "cl"] if model == "constant_lift" else ["objective", "cd", "lift_scale"]
    surface = surface.sort_values(sort_cols).reset_index(drop=True)
    surface["coarse_grid_rank"] = np.arange(1, len(surface) + 1)
    lift_column = "cl" if model == "constant_lift" else "lift_scale"
    top_n = min(3, len(surface))
    starts = [
        (
            f"grid_rank_{int(row.coarse_grid_rank)}",
            float(row.cd),
            float(getattr(row, lift_column)),
            int(row.coarse_grid_rank),
        )
        for row in surface.head(top_n).itertuples(index=False)
    ]
    midpoint_lift = float((lift_bounds[0] + lift_bounds[1]) / 2.0)
    starts.append(("midpoint", float((cd_bounds[0] + cd_bounds[1]) / 2.0), midpoint_lift, 0))
    objective_records = full_train_records if full_train_records is not None else calibration_records
    run_rows = []
    options = {
        "maxiter": int(local_optimization.get("maxiter", 40)),
        "maxfev": int(local_optimization.get("maxfev", 120)),
        "xtol": float(local_optimization.get("xtol", 1e-4)),
        "ftol": float(local_optimization.get("ftol", 1e-6)),
    }
    method = str(local_optimization.get("method", "Powell"))
    minimum_improvement = float(local_optimization.get("minimum_improvement", 1e-6))

    def local_objective(values: np.ndarray) -> float:
        cd_value = float(values[0])
        lift_value = float(values[1])
        objective, _failures = _objective(
            calibration_records,
            model=model,
            constants=constants,
            solver=solver,
            cd=cd_value,
            cl=lift_value if model == "constant_lift" else 0.0,
            lift_scale=lift_value if model == "spin_factor_lift" else 0.0,
            side_sign=side_sign,
            lateral_weight=float(lateral_weight),
            carry_definition=carry_definition,
            failure_penalty=failure_penalty,
        )
        return float(objective)

    for start_label, initial_cd, initial_lift, coarse_rank in starts:
        initial_objective, initial_failures = _objective(
            calibration_records,
            model=model,
            constants=constants,
            solver=solver,
            cd=float(initial_cd),
            cl=float(initial_lift) if model == "constant_lift" else 0.0,
            lift_scale=float(initial_lift) if model == "spin_factor_lift" else 0.0,
            side_sign=side_sign,
            lateral_weight=float(lateral_weight),
            carry_definition=carry_definition,
            failure_penalty=failure_penalty,
        )
        result = minimize(
            local_objective,
            x0=np.asarray([initial_cd, initial_lift], dtype=float),
            method=method,
            bounds=[cd_bounds, lift_bounds],
            options=options,
        )
        final_cd = float(np.clip(result.x[0], cd_bounds[0], cd_bounds[1]))
        final_lift = float(np.clip(result.x[1], lift_bounds[0], lift_bounds[1]))
        objective, failures = _objective(
            calibration_records,
            model=model,
            constants=constants,
            solver=solver,
            cd=final_cd,
            cl=final_lift if model == "constant_lift" else 0.0,
            lift_scale=final_lift if model == "spin_factor_lift" else 0.0,
            side_sign=side_sign,
            lateral_weight=float(lateral_weight),
            carry_definition=carry_definition,
            failure_penalty=failure_penalty,
        )
        termination_message = str(result.message)
        if objective > initial_objective + minimum_improvement:
            final_cd = float(initial_cd)
            final_lift = float(initial_lift)
            objective = float(initial_objective)
            failures = int(initial_failures)
            termination_message = (
                f"{termination_message}; retained initial point because local result did not improve objective"
            )
        optimizer_success = bool(result.success)
        objective_finite = bool(np.isfinite(objective))
        accepted = optimizer_success and objective_finite and int(failures) == 0
        boundary_margin = min(
            final_cd - float(cd_bounds[0]),
            float(cd_bounds[1]) - final_cd,
            final_lift - float(lift_bounds[0]),
            float(lift_bounds[1]) - final_lift,
        )
        run_rows.append(
            {
                "model": model,
                "carry_definition": carry_definition,
                "start_label": start_label,
                "coarse_grid_rank": int(coarse_rank),
                "initial_cd": float(initial_cd),
                "initial_lift": float(initial_lift),
                "final_cd": final_cd,
                "final_lift": final_lift,
                "objective": float(objective),
                "initial_objective": float(initial_objective),
                "final_objective": float(objective),
                "objective_improvement": float(initial_objective - objective),
                "optimizer_success": optimizer_success,
                "objective_finite": objective_finite,
                "accepted": accepted,
                "success": optimizer_success,
                "termination_message": termination_message,
                "message": termination_message,
                "iterations": int(getattr(result, "nit", 0)),
                "function_evaluations": int(getattr(result, "nfev", 0)),
                "calibration_n": int(len(calibration_records)),
                "calibration_failed_count": int(failures),
                "failed_count": int(failures),
                "initial_failed_count": int(initial_failures),
                "boundary_margin": float(boundary_margin),
                "selected": False,
                "full_train_objective": np.nan,
                "full_train_failed_count": np.nan,
            }
        )

    runs = pd.DataFrame(run_rows)
    accepted_runs = runs[runs["accepted"].astype(bool)]
    if accepted_runs.empty:
        raise RuntimeError(f"{model} calibration failed: no accepted local optimization run")
    best = accepted_runs.sort_values(
        ["final_objective", "boundary_margin", "final_cd", "final_lift"],
        ascending=[True, False, True, True],
    ).iloc[0]
    best_index = best.name
    params = {
        "cd": float(best["final_cd"]),
        "cl": float(best["final_lift"]) if model == "constant_lift" else 0.0,
        "lift_scale": float(best["final_lift"]) if model == "spin_factor_lift" else 0.0,
    }
    full_train_objective, full_train_failures = _objective(
        objective_records,
        model=model,
        constants=constants,
        solver=solver,
        cd=params["cd"],
        cl=params["cl"],
        lift_scale=params["lift_scale"],
        side_sign=side_sign,
        lateral_weight=float(lateral_weight),
        carry_definition=carry_definition,
        failure_penalty=failure_penalty,
    )
    runs.loc[best_index, "selected"] = True
    runs.loc[best_index, "full_train_objective"] = float(full_train_objective)
    runs.loc[best_index, "full_train_failed_count"] = int(full_train_failures)
    if return_runs:
        return params, surface, runs
    return params, surface


def evaluate_ode_models(
    test: pd.DataFrame,
    *,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    parameters: dict[str, dict[str, float]],
    carry_definition: str,
    model_variants: list[str] | None = None,
    side_sign: int = 1,
) -> dict[str, pd.DataFrame]:
    if model_variants is None:
        model_variants = ODE_MODELS
    prediction_rows = []
    failure_rows = []
    for model in model_variants:
        failed_ids = []
        model_params = parameters.get(model, {})
        for _, row in test.iterrows():
            pred, _ = simulate_shot(
                row,
                model=model,
                constants=constants,
                solver=solver,
                cd=float(model_params.get("cd", 0.0)),
                cl=float(model_params.get("cl", 0.0)),
                lift_scale=float(model_params.get("lift_scale", 0.0)),
                side_sign=side_sign,
                carry_definition=carry_definition,
            )
            if pred["integration_status"] != "success":
                failed_ids.append(int(row["record_id"]))
            prediction_rows.append(
                {
                    "record_id": int(row["record_id"]),
                    "sample_id": int(row["record_id"]),
                    "model": model,
                    "carry_definition": carry_definition,
                    "actual_carry_yd": float(row["carry_distance_yd"]),
                    "predicted_carry_yd": pred["predicted_carry_yd"],
                    "predicted_x_carry_yd": pred["predicted_x_carry_yd"],
                    "predicted_radial_carry_yd": pred["predicted_radial_carry_yd"],
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


def typical_errors_and_trajectories(
    typical_source: pd.DataFrame,
    *,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    parameters: dict[str, dict[str, float]],
    model_variants: list[str],
    trajectory_model: str,
    side_sign: int,
    carry_definition: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    error_rows = []
    trajectory_rows = []
    for _, row in typical_source.iterrows():
        for model in model_variants:
            params = parameters.get(model, {})
            keep_trajectory = model == trajectory_model
            pred, trajectory = simulate_shot(
                row,
                model=model,
                constants=constants,
                solver=solver,
                cd=float(params.get("cd", 0.0)),
                cl=float(params.get("cl", 0.0)),
                lift_scale=float(params.get("lift_scale", 0.0)),
                side_sign=side_sign,
                keep_trajectory=keep_trajectory,
                carry_definition=carry_definition,
            )
            carry_error = pred["predicted_carry_yd"] - float(row["carry_distance_yd"])
            apex_error = pred["predicted_apex_yd"] - float(row["apex_height_yd"])
            lateral_error = pred["predicted_lateral_yd"] - float(row["lateral_offset_yd"])
            error_rows.append(
                {
                    "sample_id": int(row["record_id"]),
                    "record_id": int(row["record_id"]),
                    "target_group": str(row["target_group"]),
                    "model": model,
                    "carry_definition": carry_definition,
                    "actual_carry_yd": float(row["carry_distance_yd"]),
                    "predicted_carry_yd": pred["predicted_carry_yd"],
                    "predicted_x_carry_yd": pred["predicted_x_carry_yd"],
                    "predicted_radial_carry_yd": pred["predicted_radial_carry_yd"],
                    "carry_absolute_error_yd": abs(carry_error),
                    "carry_relative_error_pct": abs(carry_error / float(row["carry_distance_yd"])) * 100.0,
                    "actual_apex_yd": float(row["apex_height_yd"]),
                    "predicted_apex_yd": pred["predicted_apex_yd"],
                    "apex_absolute_error_yd": abs(apex_error),
                    "apex_relative_error_pct": abs(apex_error / float(row["apex_height_yd"])) * 100.0
                    if abs(float(row["apex_height_yd"])) > 1e-12
                    else np.nan,
                    "actual_lateral_yd": float(row["lateral_offset_yd"]),
                    "predicted_lateral_yd": pred["predicted_lateral_yd"],
                    "lateral_absolute_error_yd": abs(lateral_error),
                    "flight_time_s": pred["flight_time_s"],
                    "integration_status": pred["integration_status"],
                }
            )
            if keep_trajectory:
                trajectory = trajectory.copy()
                trajectory.insert(0, "model", model)
                trajectory.insert(0, "target_group", str(row["target_group"]))
                trajectory.insert(0, "sample_id", int(row["record_id"]))
                trajectory_rows.append(trajectory)
    return pd.DataFrame(error_rows), pd.concat(trajectory_rows, ignore_index=True)


def ode_sensitivity(
    typical_source: pd.DataFrame,
    *,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    baseline_params: dict[str, float] | dict[str, dict[str, float]],
    relative_changes: list[float],
    side_sign: int,
    carry_definition: str,
    models: list[str] | None = None,
    initial_heights_m: list[float] | None = None,
) -> pd.DataFrame:
    rows = []
    if initial_heights_m is None:
        initial_heights_m = [0.001, 0.01, 0.05]
    if models is None:
        if "cd" in baseline_params:
            model_params = {"spin_factor_lift": baseline_params}  # type: ignore[dict-item]
            models = ["spin_factor_lift"]
        else:
            model_params = baseline_params  # type: ignore[assignment]
            models = list(model_params)
    else:
        model_params = baseline_params  # type: ignore[assignment]

    for model in models:
        params_for_model = dict(model_params[model])
        baseline = _scenario_means(
            typical_source,
            model=model,
            constants=constants,
            solver=solver,
            params=params_for_model,
            side_sign=side_sign,
            carry_definition=carry_definition,
        )

        parameter_names = ["cd", "cl"] if model == "constant_lift" else ["cd", "lift_scale"]
        for parameter in parameter_names:
            for change in relative_changes:
                params = dict(params_for_model)
                params[parameter] = max(0.0, float(params[parameter]) * (1.0 + float(change)))
                scenario = _scenario_means(
                    typical_source,
                    model=model,
                    constants=constants,
                    solver=solver,
                    params=params,
                    side_sign=side_sign,
                    carry_definition=carry_definition,
                )
                for metric, baseline_value in baseline.items():
                    rows.append(
                        {
                            "model": model,
                            "sensitivity_type": "parameter",
                            "parameter": parameter,
                            "relative_change": float(change),
                            "metric": metric,
                            "carry_definition": carry_definition if metric == "carry_yd" else "",
                            "baseline_value": baseline_value,
                            "scenario_value": scenario[metric],
                            "delta": scenario[metric] - baseline_value,
                        }
                    )

        wind_scenarios = {
            "no_wind": (0.0, 0.0, 0.0),
            "tailwind_1mps": (1.0, 0.0, 0.0),
            "headwind_1mps": (-1.0, 0.0, 0.0),
        }
        for parameter, wind_mps in wind_scenarios.items():
            scenario = _scenario_means(
                typical_source,
                model=model,
                constants=constants,
                solver=solver,
                params=params_for_model,
                side_sign=side_sign,
                wind_mps=wind_mps,
                carry_definition=carry_definition,
            )
            for metric, baseline_value in baseline.items():
                rows.append(
                    {
                        "model": model,
                        "sensitivity_type": "wind",
                        "parameter": parameter,
                        "relative_change": np.nan,
                        "wind_x_mps": float(wind_mps[0]),
                        "metric": metric,
                        "carry_definition": carry_definition if metric == "carry_yd" else "",
                        "baseline_value": baseline_value,
                        "scenario_value": scenario[metric],
                        "delta": scenario[metric] - baseline_value,
                    }
                )

        for parameter, spin_decay_s in {"spin_decay_6s": 6.0, "spin_decay_3s": 3.0}.items():
            scenario = _scenario_means(
                typical_source,
                model=model,
                constants=constants,
                solver=solver,
                params=params_for_model,
                side_sign=side_sign,
                spin_decay_s=spin_decay_s,
                carry_definition=carry_definition,
            )
            for metric, baseline_value in baseline.items():
                rows.append(
                    {
                        "model": model,
                        "sensitivity_type": "spin_decay",
                        "parameter": parameter,
                        "relative_change": np.nan,
                        "metric": metric,
                        "carry_definition": carry_definition if metric == "carry_yd" else "",
                        "baseline_value": baseline_value,
                        "scenario_value": scenario[metric],
                        "delta": scenario[metric] - baseline_value,
                    }
                )

        solver_scenarios = [
            ("rtol_x10", {**solver, "rtol": max(float(solver.get("rtol", 1e-7)) * 10.0, 1e-12)}),
            ("atol_x10", {**solver, "atol": max(float(solver.get("atol", 1e-9)) * 10.0, 1e-12)}),
            ("max_step_x2", {**solver, "max_step": float(solver.get("max_step", 0.02)) * 2.0}),
            ("method_RK45", {**solver, "method": "RK45"}),
        ]
        for parameter, scenario_solver in solver_scenarios:
            scenario = _scenario_means(
                typical_source,
                model=model,
                constants=constants,
                solver=scenario_solver,
                params=params_for_model,
                side_sign=side_sign,
                carry_definition=carry_definition,
            )
            for metric, baseline_value in baseline.items():
                rows.append(
                    {
                        "model": model,
                        "sensitivity_type": "solver_tolerance",
                        "parameter": parameter,
                        "relative_change": np.nan,
                        "metric": metric,
                        "carry_definition": carry_definition if metric == "carry_yd" else "",
                        "baseline_value": baseline_value,
                        "scenario_value": scenario[metric],
                        "delta": scenario[metric] - baseline_value,
                    }
                )

        for initial_height in initial_heights_m:
            height_constants = constants.with_initial_height(float(initial_height))
            scenario = _scenario_means(
                typical_source,
                model=model,
                constants=height_constants,
                solver=solver,
                params=params_for_model,
                side_sign=side_sign,
                carry_definition=carry_definition,
            )
            for metric, baseline_value in baseline.items():
                rows.append(
                    {
                        "model": model,
                        "sensitivity_type": "initial_height",
                        "parameter": f"initial_height_{float(initial_height):.3g}m",
                        "relative_change": np.nan,
                        "metric": metric,
                        "carry_definition": carry_definition if metric == "carry_yd" else "",
                        "baseline_value": baseline_value,
                        "scenario_value": scenario[metric],
                        "delta": scenario[metric] - baseline_value,
                    }
                )
    return pd.DataFrame(rows)


def _scenario_means(
    records: pd.DataFrame,
    *,
    model: str,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    params: dict[str, float],
    side_sign: int,
    carry_definition: str,
    wind_mps: tuple[float, float, float] = (0.0, 0.0, 0.0),
    spin_decay_s: float | None = None,
) -> dict[str, float]:
    outputs = []
    for _, row in records.iterrows():
        pred, _ = simulate_shot(
            row,
            model=model,
            constants=constants,
            solver=solver,
            cd=float(params.get("cd", 0.0)),
            cl=float(params.get("cl", 0.0)),
            lift_scale=float(params.get("lift_scale", 0.0)),
            side_sign=side_sign,
            wind_mps=wind_mps,
            spin_decay_s=spin_decay_s,
            carry_definition=carry_definition,
        )
        outputs.append(pred)
    frame = pd.DataFrame(outputs)
    return {
        "carry_yd": float(frame["predicted_carry_yd"].mean()),
        "apex_yd": float(frame["predicted_apex_yd"].mean()),
        "lateral_yd": float(frame["predicted_lateral_yd"].mean()),
        "flight_time_s": float(frame["flight_time_s"].mean()),
    }


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(math.sqrt(np.mean((predicted - actual) ** 2))) if len(actual) else np.nan


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = np.abs(actual) > 1e-12
    return float(np.mean(np.abs((predicted[mask] - actual[mask]) / actual[mask])) * 100.0) if mask.any() else np.nan


def _r2(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) == 0:
        return np.nan
    total = float(np.sum((actual - np.mean(actual)) ** 2))
    if total <= 1e-12:
        return np.nan
    residual = float(np.sum((actual - predicted) ** 2))
    return float(1.0 - residual / total)


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
                "carry_mae": float(np.mean(np.abs(carry_pred - carry_actual))) if len(ok) else np.nan,
                "carry_mape": _mape(carry_actual, carry_pred),
                "carry_r2": _r2(carry_actual, carry_pred),
                "apex_rmse": _rmse(apex_actual, apex_pred),
                "apex_mae": float(np.mean(np.abs(apex_pred - apex_actual))) if len(ok) else np.nan,
                "apex_mape": _mape(apex_actual, apex_pred),
                "apex_r2": _r2(apex_actual, apex_pred),
                "lateral_mae": float(np.mean(np.abs(lateral_pred - lateral_actual))) if len(ok) else np.nan,
                "flight_failure_rate": float(1.0 - len(ok) / len(subset)),
            }
        )
    return pd.DataFrame(rows).sort_values("model").reset_index(drop=True)


def carry_definition_comparison(predictions: pd.DataFrame, *, primary_definition: str) -> pd.DataFrame:
    rows = []
    for model, subset in predictions.groupby("model"):
        ok = subset[subset["integration_status"] == "success"].copy()
        if ok.empty:
            continue
        definitions = [
            (
                "D_x",
                "carry_distance_yd",
                "predicted_x_carry_yd",
                ok["actual_carry_yd"].to_numpy(dtype=float),
                ok["predicted_x_carry_yd"].to_numpy(dtype=float),
            ),
            (
                "D_r",
                "sqrt(carry_distance_yd^2 + lateral_offset_yd^2)",
                "predicted_radial_carry_yd",
                np.sqrt(
                    ok["actual_carry_yd"].to_numpy(dtype=float) ** 2
                    + ok["actual_lateral_yd"].to_numpy(dtype=float) ** 2
                ),
                ok["predicted_radial_carry_yd"].to_numpy(dtype=float),
            ),
        ]
        primary_label = "D_x" if primary_definition == "forward_x" else "D_r"
        for definition, actual_definition, predicted_definition, actual, predicted in definitions:
            error = predicted - actual
            rows.append(
                {
                    "model": model,
                    "carry_definition": definition,
                    "actual_definition": actual_definition,
                    "predicted_definition": predicted_definition,
                    "is_primary_definition": definition == primary_label,
                    "rmse": _rmse(actual, predicted),
                    "mae": float(np.mean(np.abs(error))),
                    "mape": _mape(actual, predicted),
                    "bias": float(np.mean(error)),
                }
            )
    return pd.DataFrame(rows).sort_values(["model", "carry_definition"]).reset_index(drop=True)


def calibration_failure_rows(
    records: pd.DataFrame,
    *,
    model: str,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    params: dict[str, float],
    side_sign: int,
    carry_definition: str,
    stage: str,
) -> pd.DataFrame:
    rows = []
    for _, row in records.iterrows():
        pred, _ = simulate_shot(
            row,
            model=model,
            constants=constants,
            solver=solver,
            cd=float(params.get("cd", 0.0)),
            cl=float(params.get("cl", 0.0)),
            lift_scale=float(params.get("lift_scale", 0.0)),
            side_sign=side_sign,
            carry_definition=carry_definition,
        )
        if pred["integration_status"] != "success":
            rows.append(
                {
                    "model": model,
                    "record_id": int(row["record_id"]),
                    "stage": stage,
                    "integration_status": pred["integration_status"],
                    "solver_message": pred["solver_message"],
                }
            )
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(
        [
            {
                "model": model,
                "record_id": np.nan,
                "stage": stage,
                "integration_status": "success",
                "solver_message": "no calibration integration failures",
            }
        ]
    )


def q3_boundary_stability_checks(
    records: pd.DataFrame,
    *,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    params: dict[str, float],
    side_sign: int,
    carry_definition: str,
) -> pd.DataFrame:
    boundary_features = ["ball_speed_mph", "launch_angle_deg", "spin_rate_rpm", "spin_axis_deg"]
    ranges = {
        feature: (
            float(records[feature].min()),
            float(records[feature].max()),
        )
        for feature in boundary_features
    }
    base = records.iloc[0].copy()
    rows = []
    outputs = []
    for speed in ranges["ball_speed_mph"]:
        for angle in ranges["launch_angle_deg"]:
            for spin_rate in ranges["spin_rate_rpm"]:
                for spin_axis in ranges["spin_axis_deg"]:
                    row = base.copy()
                    row["ball_speed_mph"] = speed
                    row["launch_angle_deg"] = angle
                    row["launch_direction_deg"] = 0.0
                    row["spin_rate_rpm"] = spin_rate
                    row["spin_axis_deg"] = spin_axis
                    pred, _ = simulate_shot(
                        row,
                        model="spin_factor_lift",
                        constants=constants,
                        solver=solver,
                        cd=float(params.get("cd", 0.0)),
                        lift_scale=float(params.get("lift_scale", 0.0)),
                        side_sign=side_sign,
                        carry_definition=carry_definition,
                    )
                    outputs.append(pred)
                    rows.append(
                        {
                            "ball_speed_mph": speed,
                            "launch_angle_deg": angle,
                            "spin_rate_rpm": spin_rate,
                            "spin_axis_deg": spin_axis,
                            "integration_status": pred["integration_status"],
                            "flight_time_s": pred["flight_time_s"],
                            "predicted_apex_yd": pred["predicted_apex_yd"],
                            "predicted_lateral_yd": pred["predicted_lateral_yd"],
                        }
                    )
    frame = pd.DataFrame(rows)
    status_ok = frame["integration_status"].eq("success").all()
    finite_ok = frame[["flight_time_s", "predicted_apex_yd", "predicted_lateral_yd"]].notna().all().all()
    max_time = float(frame["flight_time_s"].max())
    max_apex = float(frame["predicted_apex_yd"].max())
    max_lateral = float(frame["predicted_lateral_yd"].abs().max())
    checks = [
        {
            "check": "q3_spin_factor_boundary_stability",
            "passed": bool(status_ok and finite_ok),
            "value": float(len(frame)),
        },
        {
            "check": "q3_spin_factor_boundary_max_flight_time_within_limit",
            "passed": bool(np.isfinite(max_time) and max_time <= 12.0),
            "value": max_time,
        },
        {
            "check": "q3_spin_factor_boundary_max_apex_within_limit",
            "passed": bool(np.isfinite(max_apex) and max_apex <= 300.0),
            "value": max_apex,
        },
        {
            "check": "q3_spin_factor_boundary_max_lateral_within_limit",
            "passed": bool(np.isfinite(max_lateral) and max_lateral <= 400.0),
            "value": max_lateral,
        },
    ]
    return pd.DataFrame(checks)


def validation_checks(
    sample_row: pd.Series,
    *,
    constants: PhysicalConstants,
    solver: dict[str, Any],
    carry_definition: str,
    cd: float,
    cl: float = 0.20,
    lift_scale: float = 1.0,
    side_sign: int = 1,
) -> pd.DataFrame:
    vacuum_numeric, _ = simulate_shot(
        sample_row,
        model="vacuum",
        constants=constants,
        solver=solver,
        carry_definition=carry_definition,
    )
    vacuum_exact = vacuum_analytic(sample_row, constants, carry_definition=carry_definition)
    max_error = max(
        abs(vacuum_numeric["predicted_carry_yd"] - vacuum_exact["predicted_carry_yd"]),
        abs(vacuum_numeric["predicted_apex_yd"] - vacuum_exact["predicted_apex_yd"]),
        abs(vacuum_numeric["flight_time_s"] - vacuum_exact["flight_time_s"]),
    )
    drag_numeric, _ = simulate_shot(
        sample_row,
        model="drag",
        constants=constants,
        solver=solver,
        cd=cd,
        carry_definition=carry_definition,
    )

    lift_probe = sample_row.copy()
    lift_probe["launch_direction_deg"] = 0.0
    lift_probe["spin_axis_deg"] = 0.0
    drag_probe, _ = simulate_shot(
        lift_probe,
        model="drag",
        constants=constants,
        solver=solver,
        cd=max(cd, 0.1),
        carry_definition=carry_definition,
    )
    lift_probe_out, _ = simulate_shot(
        lift_probe,
        model="constant_lift",
        constants=constants,
        solver=solver,
        cd=max(cd, 0.1),
        cl=max(cl, 0.05),
        side_sign=side_sign,
        carry_definition=carry_definition,
    )
    spin_probe_out, _ = simulate_shot(
        lift_probe,
        model="spin_factor_lift",
        constants=constants,
        solver=solver,
        cd=max(cd, 0.1),
        lift_scale=max(lift_scale, 0.1),
        side_sign=side_sign,
        carry_definition=carry_definition,
    )
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
        {
            "check": "positive_backspin_lifts_up",
            "passed": lift_probe_out["predicted_apex_yd"] > drag_probe["predicted_apex_yd"],
            "value": float(lift_probe_out["predicted_apex_yd"] - drag_probe["predicted_apex_yd"]),
        },
        {
            "check": "zero_sidespin_zero_direction_lateral_near_zero",
            "passed": abs(lift_probe_out["predicted_lateral_yd"]) < 1e-6,
            "value": float(lift_probe_out["predicted_lateral_yd"]),
        },
        {
            "check": "spin_factor_lift_integrates",
            "passed": spin_probe_out["integration_status"] == "success",
            "value": float(spin_probe_out["predicted_apex_yd"]),
        },
    ]
    return pd.DataFrame(rows)
