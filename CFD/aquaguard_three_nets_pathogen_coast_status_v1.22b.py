from __future__ import annotations
import os
import tempfile
import time
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'mplconfig_aquaguard'))
import matplotlib
matplotlib.use('Agg')

"""
AquaGuard local coastal pathogen model for three nets
================================================

Purpose
-------
This program is a fast local screening model for pathogen plume / exposure
transport in and around a fish-farm layout with three circular nets near a
coastline. The model is intended for scenario analysis, rapid comparison of
flow directions, and estimation of:
- first arrival time of algae to each net
- residence time / exposure time inside each net
- relative active pathogen concentration inside the nets
- qualitative risk development over time

The code is deliberately simpler and faster than a full 3D hydrodynamic and
ecological simulator. It is therefore suitable for engineering screening,
decision support, and development of AquaGuard logic, but it should not be
interpreted as a complete ecological truth model.

Physical and numerical idea
---------------------------
The model combines four main parts:

1) Coastal background flow
   A time-varying coastal current is prescribed. The coastline is treated as a
   no-normal-flow boundary in a simplified local sense, so the background flow
   is redirected along the coast rather than through land.

2) Local net-flow response
   Each fish net is represented as a circular porous obstacle in plan view.
   The external flow around a net is approximated as:
       free/background flow + scaled potential-flow perturbation
   where the perturbation strength depends on net solidity. This gives a fast
   estimate of how the nets locally deflect the surrounding current.

3) Sequential Løland transmission through the net
   When flow crosses a net, only the normal component is reduced. The
   transmission factor per net layer is:
       beta = 1 - S_n * C_r
   where:
       S_n = net solidity [-]
       C_r = resistance coefficient [-]
   Tangential flow is retained. This gives a practical engineering description
   of how current is reduced through the net while still allowing along-net
   motion.

4) Time-marching pathogen transport
   pathogen is represented by particles that are released from an upstream source.
   For each time step, particles are advected by the local flow field and
   dispersed with a simple stochastic diffusion term. Particles can reflect
   from the coast and can pass through the nets according to the local flow
   and geometry.

Simple pathogen biology module
---------------------
Version 1.16 adds a simple biological activity / infectivity model for pathogen.
The intention is not to describe species biology in detail, but to make the
transport model more relevant for real pathogen scenarios by letting the active
algal risk decay over time.

Each particle carries:
- mass                  : transported pathogen amount
- infectivity             : remaining active biological risk, dimensionless [-]
- infectious_mass           : mass * infectivity

The infectivity is updated each time step with exponential decay:
    m_(t+dt) = m_t * exp(-k_eff * dt)

where k_eff is an effective decay rate that can be scaled by:
- base decay rate
- temperature factor
- light factor
- species infectivity / risk factor

This means that a particle can still be transported physically, but its
"active pathogen risk" becomes smaller with time. This is a useful first
approximation for declining pathogen infectivity, loss of viability relevance, or
reduced biological hazard during transport.

Model scope and limitations
---------------------------
Included in this version:
- 2D horizontal transport in plan view
- advection
- stochastic diffusion
- reflection against coast
- local net transmission / shielding
- simple biological decay of active pathogen risk
- relative concentration and exposure metrics per net

Not yet included:
- full 3D hydrodynamics
- vertical migration / depth preference
- explicit nutrient dynamics
- species-specific physiology in detail
- full CFD, turbulence closure, or wake-resolving solver
- full advection-diffusion-reaction concentration equation on a mesh

Recommended interpretation
--------------------------
Use this model to compare scenarios and identify relative differences, such as:
- which flow direction is most critical
- which net receives pathogen exposure first
- whether a tighter net increases shielding but also retention time
- how coastline position changes advection paths
- how biological decay changes active risk curves

Do not use this version alone as the final basis for regulatory or
high-stakes ecological conclusions without additional validation.

User workflow
-------------
1) Edit the USER SETTINGS section near the top of the file.
2) Run the model with run_demo().
3) Inspect geometry preview, flow plots, pathogen plots, and CSV summaries.
4) Compare cases and adjust the scenario as needed.

Units
-----
- length: m
- depth: m
- velocity: m/s
- time: s
- diffusion: m²/s
- concentration/risk outputs: relative, dimensionless screening metrics
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import json
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =============================================================================
# USER SETTINGS – EDIT THESE VALUES FIRST
# =============================================================================
# Denne seksjonen er laget for brukere som vil endre scenarioet i Spyder uten
# å lete inne i klassene. Standardverdiene under brukes automatisk når run_demo()
# kjøres. Endringer her slår direkte inn i både strømningsmodell og pathogen-modul.
#
# Viktig om enheter:
# - hastighet: m/s
# - lengde/avstand/dybde: m
# - tid: s
# - diffusjon: m²/s
# - soliditet og andre faktorer: dimensjonsløse [-]
# =============================================================================

FLOW_USER_SETTINGS = {
    # Referanse fri-strøm [m/s]. Skalerer basisnivået i kyststrømmen og hvor
    # raskt patogener transporteres gjennom domenet. Høyere verdi gir generelt
    # raskere ankomst og kortere oppholdstid.
    'U_inf': 0.5,

    # Mappe for lagring av PNG/CSV/JSON. Hvis None brukes "output" ved siden av
    # Python-filen. Kan settes til f.eks. Path.cwd() / "mine_resultater".
    'output_dir': None,
}

NET_USER_SETTINGS = [
    {
        'name': 'Net 1',
        'center': (-100.0, 0.0),  # (x, y) [m]
        'radius': 25.0,           # radius [m] -> diameter 50 m
        'depth': 5.0,             # notdybde [m] i denne 2D-planmodellen
        'solidity': 0.25,         # S_n [-], lav verdi = mer åpen not
        'Cr': 0.8,                # Løland motstandskoeffisient [-]
    },
    {
        'name': 'Net 2',
        'center': (0.0, 0.0),
        'radius': 25.0,
        'depth': 5.0,
        'solidity': 0.60,
        'Cr': 0.8,
    },
    {
        'name': 'Net 3',
        'center': (100.0, 0.0),
        'radius': 25.0,
        'depth': 5.0,
        'solidity': 0.95,
        'Cr': 0.8,
    },
]

COAST_USER_SETTINGS = {
    # Kystlinjens plassering [m] i modellplanet. Alle punkter med lavere y enn
    # y_coast regnes som land i denne versjonen.
    'y_coast': -150.0,

    # Romlig variasjonslengde [m] for langs-kyst strøm. Lavere verdi gir raskere
    # variasjon langs kysten.
    'alongshore_length_scale_m': 220.0,

    # Avtagingslengde [m] for hvor langt ut fra kysten den ekstra langs-kyst
    # komponenten påvirker strømfeltet.
    'offshore_decay_m': 120.0,

    # Tidsperiode [s] for enkel pulsering av langs-kyst strømmen.
    'temporal_period_s': 900.0,

    # Relativ amplitude [-] for romlig/tidslig variasjon i langs-kyst strømmen.
    'alongshore_variation_fraction': 0.30,

    # Vekt [-] for speilbidrag mot kysten. Høyere verdi gjør kysten mer
    # "hindrende" i den raske strømningsmodellen.
    'wall_image_weight': 0.85,
}

DOMAIN_USER_SETTINGS = {
    # Beregningsdomene for feltplot og snapshots [m]. Øk om du vil se større
    # område rundt anlegget, men det øker kjøretiden.
    'x': (-260.0, 260.0),
    'y_top': 180.0,

    # Feltoppløsning for snapshot/flow-plott. Høyere verdi gir finere figurer,
    # men tregere kjøring.
    'nx': 241,
    'ny': 181,
}


PATHOGEN_USER_SETTINGS = {
    'pathogen_name': 'Generic pathogen',
    'dt_s': 10.0,
    'total_time_s': 1200.0,
    'particles_per_step': 9,
    'source_mode': 'upstream_line',  # 'upstream_line' | 'infected_net'
    'source_net_name': 'Net 1',
    'source_load': 1.0,
    'shedding_rate_relative_per_s': 1.0,
    'source_patch_radius_fraction': 0.35,
    'source_infectivity': 1.0,
    'diffusion_m2_s': 0.12,
    'biology_enabled': True,
    'base_inactivation_rate_1_s': 1.65e-6,
    'temperature_c': 10.0,
    'reference_temperature_c': 10.0,
    'q10_inactivation': 1.5,
    'uv_inactivation_factor': 1.0,
    'species_infectivity_factor': 1.0,
    'vertical_preference_mode': 'none',
    'minimum_infectivity': 1.0e-3,
    'random_seed': 42,
    'verbose': True,
    'progress_every_pct': 10.0,
}

pathogen_USER_SETTINGS = PATHOGEN_USER_SETTINGS

RISK_USER_SETTINGS = {
    # Operativ risikomotor basert på eksisterende KPI-er.
    # Tersklene under er relative screeninggrenser og bør justeres mot erfaring,
    # prøvedata og eventuelle arts-/lokalitets-spesifikke krav.
    #
    # Nytt i v1.22:
    # Peak- og eksponeringsterskler kan kalibreres automatisk fra første
    # patogenanalyse (baseline-case). Dette er en screeningkalibrering av
    # modellens egen skala, ikke en biologisk fasit.

    # Alarm hvis første ankomst skjer raskere enn denne terskelen [s].
    'arrival_alarm_threshold_s': 900.0,

    # Alarm hvis total risiko-vektet eksponering overstiger denne terskelen
    # [relativ masse * s].
    'exposure_alarm_threshold_mass_seconds': 80.0,

    # Gule terskler for operativ klassifisering.
    'yellow_arrival_threshold_s': 1200.0,
    'yellow_peak_risk_concentration': 0.010,
    'yellow_exposure_threshold_mass_seconds': 40.0,

    # Røde terskler for operativ klassifisering.
    'red_arrival_threshold_s': 600.0,
    'red_peak_risk_concentration': 0.025,
    'red_exposure_threshold_mass_seconds': 100.0,

    # Hvis True gir manglende ankomst alltid grønn status, selv om andre KPI-er
    # er null/NaN.
    'no_arrival_means_green': True,

    # Automatisk baseline-kalibrering av peak- og eksponeringsterskler.
    'auto_calibrate_from_first_case': True,
    'baseline_case_name': 'langs',
    'baseline_peak_reference': 'max',      # 'max' eller 'mean'
    'baseline_exposure_reference': 'max',  # 'max' eller 'mean'
    'yellow_peak_factor': 1.50,
    'red_peak_factor': 2.50,
    'yellow_exposure_factor': 1.50,
    'red_exposure_factor': 2.50,
    'baseline_min_peak': 0.0020,
    'baseline_min_exposure': 10.0,
}

RUN_USER_SETTINGS = {
    # Hvilke strømretninger som skal analyseres når run_demo() kjøres.
    'cases': ['langs', 'tverrs', 'diagonal'],

    # Hvis True kjøres run_demo() automatisk når fila kjøres som script.
    'auto_run_when_main': True,
}


@dataclass
class Net:
    name: str
    center: Tuple[float, float]
    radius: float
    depth: float
    solidity: float
    Cr: float = 0.8

    @property
    def is_impermeable(self) -> bool:
        """Returnerer True hvis noten skal behandles som helt tett."""
        return self.solidity >= 1.0 - 1e-12

    @property
    def beta(self) -> float:
        """
        Én-lags transmisjonsfaktor for normalhastighet gjennom noten.

        Viktig i v1.21:
        - Hvis ``solidity >= 1.0`` behandles noten som helt tett og ``beta=0``.
        - Dette gjør at ``Sn=1.0`` faktisk betyr null transmisjon, ikke 20 %
          slik den generelle Løland-formelen ville gitt når ``Cr=0.8``.
        """
        if self.is_impermeable:
            return 0.0
        return max(0.0, 1.0 - self.solidity * self.Cr)

    @property
    def beta2(self) -> float:
        return self.beta ** 2

    @property
    def opacity(self) -> float:
        if self.is_impermeable:
            return 1.0
        return min(1.0, max(0.0, 1.0 - self.beta))

    @property
    def plan_area(self) -> float:
        return math.pi * self.radius ** 2



@dataclass
class pathogenParticle:
    x: float
    y: float
    mass: float
    birth_time_s: float
    infectivity: float = 1.0
    alive: bool = True
    entered_once: Dict[str, bool] = field(default_factory=dict)
    exposure_s: Dict[str, float] = field(default_factory=dict)

@dataclass
class StraightCoastline:
    """
    Enkel parameterisering av rett kystlinje brukt i kyst-pathogen-caset.

    Parametere
    ----------
    y_coast : float, default -150.0
        Kystlinjens plassering i modellplanet [m]. Alle punkter med lavere
        y-verdi regnes som land i denne versjonen.

    alongshore_length_scale_m : float, default 220.0
        Romlig variasjonslengde [m] for langs-kyst strømkomponenten.
        Lavere verdi gir raskere variasjon langs kysten, høyere verdi gir
        glattere langs-kyst strøm.

    offshore_decay_m : float, default 120.0
        Avtagingslengde [m] for hvor raskt den ekstra langs-kyst komponenten
        dør ut med avstand fra kysten. Høyere verdi gir større kystpåvirket sone.

    temporal_period_s : float, default 900.0
        Periode [s] for tidsvariasjon i den langs-kyst strømmen. Kan tolkes som
        en enkel representasjon av pulsering fra tidevann/vind.

    alongshore_variation_fraction : float, default 0.30
        Relativ amplitudefaktor [-] for romlig/tidslig variasjon langs kysten.
        0.30 betyr omtrent ±30 % variasjon rundt basisverdien.

    wall_image_weight : float, default 0.85
        Vekt [-] for speilbidrag mot kysten. Økes denne blir kysten mer
        'hindrende' i den raske strømningsmodellen.
    """

    y_coast: float = -150.0
    alongshore_length_scale_m: float = 220.0
    offshore_decay_m: float = 120.0
    temporal_period_s: float = 900.0
    alongshore_variation_fraction: float = 0.30
    wall_image_weight: float = 0.85


class CoastalThreeNetFlowModel:
    """
    Rask lokal strømningsmodell for tre nøter ved kyst.

    Modellen kombinerer:
    - bakgrunnsstrøm nær kyst
    - skalert potensialstrømsforstyrrelse rundt hver not
    - sekvensiell Løland-transmisjon gjennom notene

    Viktig:
    - modellen er 2D i plan
    - den er laget for screening og scenarioanalyse
    - den erstatter ikke en full CFD- eller 3D-hydrodynamisk modell
    """

    def __init__(
        self,
        U_inf: float | None = None,
        output_dir: Path | None = None,
        nets: List[Net] | None = None,
        coast: StraightCoastline | None = None,
        domain: dict | None = None,
    ):
        """
        Parametere
        ----------
        U_inf : float, default 0.5
            Referanse fri-strømshastighet [m/s]. Dette er basisnivået som både
            bakgrunnsstrømmen og de lokale notforstyrrelsene skaleres med.
            Øker du denne, øker også transporthastighet, gjennomstrømning og
            vanligvis hvor raskt pathogen-partiklene når anlegget.

        output_dir : pathlib.Path | None, default None
            Mappe der figurer, CSV-er og metadata lagres. Hvis None brukes en
            lokal undermappe kalt ``output`` ved siden av Python-filen.

        Faste modellvalg i denne versjonen
        ---------------------------------
        - Tre nøter i rekke med sentre (-100, 0), (0, 0), (100, 0) [m]
        - Radius 25 m (diameter 50 m) for alle nøter
        - Dybde 5 m for alle nøter
        - Soliditet 0.25, 0.60 og 1.00 for henholdsvis Net 1, Net 2 og Net 3
        - Kystlinje 150 m fra nøtene, representert ved ``StraightCoastline``
        - Beregningsdomene definert i ``self.domain``

        Praktisk tolkning
        -----------------
        - Endre ``U_inf`` når du vil teste sterkere eller svakere basisstrøm.
        - Endre ``self.nets`` hvis du vil flytte nøter, justere soliditet eller
          endre diameter/dybde.
        - Endre ``self.coast`` hvis du vil justere kystavstand, langs-kyst
          variasjon eller tidsperioden i kyststrømmen.
        - Endre ``self.domain`` hvis du vil ha større eller finere beregningsfelt.
        """
        U_inf = FLOW_USER_SETTINGS['U_inf'] if U_inf is None else U_inf
        output_dir = FLOW_USER_SETTINGS['output_dir'] if output_dir is None else output_dir

        self.U_inf = float(U_inf)

        if nets is None:
            self.nets = [Net(**cfg) for cfg in NET_USER_SETTINGS]
        else:
            self.nets = list(nets)

        if coast is None:
            self.coast = StraightCoastline(**COAST_USER_SETTINGS)
        else:
            self.coast = coast

        if domain is None:
            self.domain = {
                'x': DOMAIN_USER_SETTINGS['x'],
                'y': (self.coast.y_coast, DOMAIN_USER_SETTINGS['y_top']),
                'nx': DOMAIN_USER_SETTINGS['nx'],
                'ny': DOMAIN_USER_SETTINGS['ny'],
            }
        else:
            self.domain = dict(domain)

        base_dir = Path(__file__).resolve().parent
        self.output_dir = (output_dir or (base_dir / 'output')).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def parameter_reference(self) -> dict:
        """Returnerer forklaring av sentrale strømningsparametere og faste modellvalg."""
        return {
            'U_inf': 'Fri referansestrøm [m/s]. Skalerer bakgrunnsstrøm og lokal nettpåvirkning.',
            'output_dir': 'Output-mappe for figurer, CSV-er og metadata.',
            'nets': [
                {
                    'name': n.name,
                    'center': f'Senter [m] = {n.center}',
                    'radius': f'Radius [m] = {n.radius}',
                    'depth': f'Dybde [m] = {n.depth}',
                    'solidity': f'Soliditet [-] = {n.solidity}',
                    'Cr': f'Løland motstandskoeffisient [-] = {n.Cr}',
                    'beta': f'En-lags transmisjon = 1 - S_n*C_r = {n.beta:.3f}',
                    'beta2': f'To-lags transmisjon = beta² = {n.beta2:.3f}',
                }
                for n in self.nets
            ],
            'coast': {
                'y_coast': 'Kystlinjens plassering [m] i modellplanet.',
                'alongshore_length_scale_m': 'Romlig variasjonslengde [m] for langs-kyst strøm.',
                'offshore_decay_m': 'Avtagingslengde [m] for kyststrømmens påvirkning offshore.',
                'temporal_period_s': 'Periode [s] for tidsvariasjon i langs-kyst strøm.',
                'alongshore_variation_fraction': 'Relativ amplitudefaktor [-] for variasjon langs kysten.',
                'wall_image_weight': 'Vekt [-] for speilbidrag fra kysten i den raske modellen.',
            },
            'domain': {
                'x': 'Beregningsområde i x-retning [m].',
                'y': 'Beregningsområde i y-retning [m].',
                'nx': 'Antall gridpunkter i x-retning for feltplot og snapshots.',
                'ny': 'Antall gridpunkter i y-retning for feltplot og snapshots.',
            },
        }

    def _log_parameter_summary(self, log_func=print) -> None:
        """Skriv ut en kort oppsummering av strømningsmodellens parametere."""
        log_func('Strømningsmodell – parameteroppsett:')
        log_func(f'  U_inf={self.U_inf:.3f} m/s -> fri referansestrøm')
        log_func(f'  output_dir={self.output_dir}')
        log_func('  Nøter:')
        for n in self.nets:
            log_func(
                f"    {n.name}: center={n.center} m | diameter={2*n.radius:.1f} m | depth={n.depth:.1f} m | "
                f"soliditet={n.solidity:.2f} | beta={n.beta:.3f} | beta²={n.beta2:.3f}"
            )
        log_func('  Kystlinje:')
        log_func(f'    y_coast={self.coast.y_coast:.1f} m | alongshore_length_scale_m={self.coast.alongshore_length_scale_m:.1f} m')
        log_func(f'    offshore_decay_m={self.coast.offshore_decay_m:.1f} m | temporal_period_s={self.coast.temporal_period_s:.1f} s')
        log_func(f'    alongshore_variation_fraction={self.coast.alongshore_variation_fraction:.2f} | wall_image_weight={self.coast.wall_image_weight:.2f}')
        log_func(f"  Domene: x={self.domain['x']} m | y={self.domain['y']} m | nx={self.domain['nx']} | ny={self.domain['ny']}")

    @staticmethod
    def _unit(vec: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(vec)
        if n < 1e-12:
            return np.array([1.0, 0.0])
        return vec / n

    @staticmethod
    def _rotate_to_local(vec: np.ndarray, e: np.ndarray, ep: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        xloc = vec[..., 0] * e[0] + vec[..., 1] * e[1]
        yloc = vec[..., 0] * ep[0] + vec[..., 1] * ep[1]
        return xloc, yloc

    @staticmethod
    def _rotate_to_global(uloc: np.ndarray, vloc: np.ndarray, e: np.ndarray, ep: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        ug = uloc * e[0] + vloc * ep[0]
        vg = uloc * e[1] + vloc * ep[1]
        return ug, vg

    @staticmethod
    def _transmit(velocity: np.ndarray, pass_normal: np.ndarray, beta: float) -> np.ndarray:
        q = float(np.dot(velocity, pass_normal))
        if q <= 0.0:
            return velocity.copy()
        v_n = q * pass_normal
        v_t = velocity - v_n
        return v_t + beta * v_n

    @staticmethod
    def case_vector(case_name: str) -> np.ndarray:
        """Returner standard strømretning for scenarioene.

        Viktig for patogenversjonen:
        - 'tverrs' og 'diagonal' peker fra åpen sjø (positiv y) inn mot kyst/anlegg,
          slik at regional kilde ('upstream_line') kommer fra sjøsiden og ikke fra kystlinjen.
        """
        cases = {
            'langs': np.array([1.0, 0.0]),
            'tverrs': np.array([0.0, -1.0]),
            'diagonal': np.array([1.0, -1.0]) / np.sqrt(2.0),
        }
        return cases[case_name]

    def _point_inside_net(self, x: float, y: float, net: Net) -> bool:
        dx = x - net.center[0]
        dy = y - net.center[1]
        return dx * dx + dy * dy <= net.radius ** 2 + 1e-12

    def coastal_background_velocity_at_point_time(self, point: np.ndarray, t_s: float, case_dir: np.ndarray) -> np.ndarray:
        x, y = float(point[0]), float(point[1])
        y_coast = self.coast.y_coast
        dist = max(y - y_coast, 0.0)
        along = np.array([1.0, 0.0])
        normal = np.array([0.0, 1.0])

        case_dir = self._unit(case_dir)
        U_along_base = self.U_inf * float(np.dot(case_dir, along))
        U_cross_base = self.U_inf * float(np.dot(case_dir, normal))

        ramp = np.tanh(dist / 25.0)
        U_cross = U_cross_base * ramp

        spatial_phase = 2.0 * np.pi * x / self.coast.alongshore_length_scale_m
        temporal_phase = 2.0 * np.pi * t_s / self.coast.temporal_period_s
        variation = 1.0 + self.coast.alongshore_variation_fraction * np.sin(spatial_phase + temporal_phase)
        offshore_decay = np.exp(-dist / self.coast.offshore_decay_m)
        U_along_variable = (0.35 * self.U_inf) * variation * offshore_decay

        Ux = U_along_base + U_along_variable
        Uy = U_cross
        return np.array([Ux, Uy])

    def _outer_perturbation_from_net(self, X: np.ndarray, Y: np.ndarray, net: Net, local_bg: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        U_mag = float(np.linalg.norm(local_bg))
        if U_mag < 1e-10:
            return np.zeros_like(X), np.zeros_like(Y)

        e = self._unit(local_bg)
        ep = np.array([-e[1], e[0]])
        dx = X - net.center[0]
        dy = Y - net.center[1]
        xloc, yloc = self._rotate_to_local(np.stack([dx, dy], axis=-1), e, ep)
        r2 = xloc ** 2 + yloc ** 2
        r = np.sqrt(np.maximum(r2, 1e-12))
        theta = np.arctan2(yloc, xloc)

        a = net.radius
        u_total = U_mag * (1.0 - (a ** 2 / np.maximum(r2, 1e-12)) * np.cos(2.0 * theta))
        v_total = -U_mag * (a ** 2 / np.maximum(r2, 1e-12)) * np.sin(2.0 * theta)
        u_pert = net.opacity * (u_total - U_mag)
        v_pert = net.opacity * v_total
        ug, vg = self._rotate_to_global(u_pert, v_pert, e, ep)
        mask_inside = r <= a
        ug = np.where(mask_inside, 0.0, ug)
        vg = np.where(mask_inside, 0.0, vg)
        return ug, vg

    def _image_perturbation_from_net(self, X: np.ndarray, Y: np.ndarray, net: Net, local_bg: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        mirrored = Net(
            name=f'{net.name}_image',
            center=(net.center[0], 2.0 * self.coast.y_coast - net.center[1]),
            radius=net.radius,
            depth=net.depth,
            solidity=net.solidity,
            Cr=net.Cr,
        )
        ug, vg = self._outer_perturbation_from_net(X, Y, mirrored, local_bg)
        return self.coast.wall_image_weight * ug, self.coast.wall_image_weight * vg

    def _events_for_point_and_net(self, point: np.ndarray, flow_dir: np.ndarray, net: Net) -> List[Tuple[float, np.ndarray, float]]:
        e = self._unit(flow_dir)
        ep = np.array([-e[1], e[0]])
        c = np.array(net.center)
        q = point - c
        s_p = float(np.dot(point, e))
        s_c = float(np.dot(c, e))
        eta = float(np.dot(q, ep))

        if abs(eta) > net.radius + 1e-12:
            return []

        xi_half = math.sqrt(max(net.radius ** 2 - eta ** 2, 0.0))
        s_front = s_c - xi_half
        s_back = s_c + xi_half
        if s_p < s_front - 1e-12:
            return []

        front_point = c + (-xi_half) * e + eta * ep
        back_point = c + (+xi_half) * e + eta * ep
        n_front_out = (front_point - c) / net.radius
        n_back_out = (back_point - c) / net.radius

        events: List[Tuple[float, np.ndarray, float]] = []
        events.append((s_front, -n_front_out, net.beta))
        if s_p > s_back + 1e-12:
            events.append((s_back, n_back_out, net.beta))
        return events

    def background_velocity_at_point_time(self, point: np.ndarray, t_s: float, case_dir: np.ndarray, exclude_index: int | None = None) -> np.ndarray:
        bg = self.coastal_background_velocity_at_point_time(point, t_s, case_dir)
        vx, vy = float(bg[0]), float(bg[1])
        X = np.array([[point[0]]])
        Y = np.array([[point[1]]])
        local_bg = bg.copy()
        for idx, net in enumerate(self.nets):
            if exclude_index is not None and idx == exclude_index:
                continue
            up, vp = self._outer_perturbation_from_net(X, Y, net, local_bg)
            vx += float(up[0, 0])
            vy += float(vp[0, 0])
            ui, vi = self._image_perturbation_from_net(X, Y, net, local_bg)
            vx += float(ui[0, 0])
            vy += float(vi[0, 0])
        return np.array([vx, vy])

    def velocity_at_point_time(self, x: float, y: float, t_s: float, case_dir: np.ndarray) -> np.ndarray:
        point = np.array([x, y], dtype=float)
        bg0 = self.coastal_background_velocity_at_point_time(point, t_s, case_dir)
        transport_dir = self._unit(bg0 if np.linalg.norm(bg0) > 1e-12 else case_dir)

        inside_indices = [i for i, net in enumerate(self.nets) if self._point_inside_net(x, y, net)]
        if len(inside_indices) > 1:
            inside_indices = inside_indices[:1]
        exclude_idx = inside_indices[0] if inside_indices else None

        v = self.background_velocity_at_point_time(point, t_s, case_dir, exclude_index=exclude_idx)
        events: List[Tuple[float, np.ndarray, float]] = []
        for net in self.nets:
            events.extend(self._events_for_point_and_net(point, transport_dir, net))
        events.sort(key=lambda tup: tup[0])
        for _, pass_normal, beta in events:
            v = self._transmit(v, pass_normal, beta)

        if y <= self.coast.y_coast + 1.0 and v[1] < 0.0:
            v[1] = 0.0
        return v

    def evaluate_field(self, case_name: str, t_s: float, nx: int | None = None, ny: int | None = None) -> dict:
        case_dir = self.case_vector(case_name)
        nx = self.domain['nx'] if nx is None else int(nx)
        ny = self.domain['ny'] if ny is None else int(ny)
        x = np.linspace(*self.domain['x'], nx)
        y = np.linspace(*self.domain['y'], ny)
        X, Y = np.meshgrid(x, y)
        U = np.zeros_like(X)
        V = np.zeros_like(X)
        water_mask = Y >= self.coast.y_coast

        for i in range(Y.shape[0]):
            for j in range(X.shape[1]):
                if not water_mask[i, j]:
                    U[i, j] = np.nan
                    V[i, j] = np.nan
                    continue
                v = self.velocity_at_point_time(float(X[i, j]), float(Y[i, j]), t_s, case_dir)
                U[i, j] = v[0]
                V[i, j] = v[1]

        speed = np.sqrt(U ** 2 + V ** 2)
        return {'X': X, 'Y': Y, 'U': U, 'V': V, 'speed': speed, 'case_name': case_name, 'time_s': t_s}



class CoastalpathogenTimeMarcher:
    """
    Time-marching pathogen-modul for lokal screening rundt tre nøter ved kyst.

    Klassen legger pathogen-partikler inn oppstrøms, flytter dem med lokalt
    strømningsfelt for hvert tidssteg og beregner relative konsentrasjoner,
    ankomsttid og oppholdstid inne i hver nøt.

    Nytt i versjon 1.17
    -------------------
    En enkel biologimodul er lagt inn for å gjøre pathogen-resultatene mer relevante.
    Hver partikkel har nå:
    - en grunnmasse ``mass`` som representerer relativ pathogen-mengde ved innløpet
    - en levedyktighet ``infectivity`` i området [0, 1]

    Den biologisk aktive massen blir da:
        infectious_mass = mass * infectivity

    og oppdateres for hvert tidssteg med:
        infectivity_{t+dt} = infectivity_t * exp(-k_eff * dt)

    hvor ``k_eff`` kan skaleres av temperatur, lys og en enkel arts-/
    toksisitetsfaktor for rapportering.

    Viktig:
    - Modellen er 2D i plan (ingen vertikal struktur i denne versjonen).
    - Konsentrasjon uttrykkes som relativ aktiv masse per planareal [masse/m²].
    - Toksisitetsfaktoren påvirker risikomål, ikke selve transportbanen.
    """

    def __init__(
        self,
        flow_model: CoastalThreeNetFlowModel,
        dt_s: float = 10.0,
        total_time_s: float = 1200.0,
        particles_per_step: int = 9,
        pathogen_name: str = 'Generic pathogen',
        source_mode: str = 'upstream_line',
        source_net_name: str | None = 'Net 1',
        source_load: float = 1.0,
        shedding_rate_relative_per_s: float = 1.0,
        source_patch_radius_fraction: float = 0.35,
        source_infectivity: float = 1.0,
        diffusion_m2_s: float = 0.12,
        biology_enabled: bool = True,
        base_inactivation_rate_1_s: float = 5.0e-4,
        temperature_c: float = 10.0,
        reference_temperature_c: float = 10.0,
        q10_inactivation: float = 1.5,
        uv_inactivation_factor: float = 1.0,
        species_infectivity_factor: float = 1.0,
        vertical_preference_mode: str = 'none',
        minimum_infectivity: float = 1.0e-3,
        arrival_alarm_threshold_s: float = 900.0,
        exposure_alarm_threshold_mass_seconds: float = 80.0,
        yellow_arrival_threshold_s: float = 1200.0,
        yellow_peak_risk_concentration: float = 0.010,
        yellow_exposure_threshold_mass_seconds: float = 40.0,
        red_arrival_threshold_s: float = 600.0,
        red_peak_risk_concentration: float = 0.025,
        red_exposure_threshold_mass_seconds: float = 100.0,
        no_arrival_means_green: bool = True,
        auto_calibrate_from_first_case: bool = True,
        baseline_case_name: str = 'langs',
        baseline_peak_reference: str = 'max',
        baseline_exposure_reference: str = 'max',
        yellow_peak_factor: float = 1.50,
        red_peak_factor: float = 2.50,
        yellow_exposure_factor: float = 1.50,
        red_exposure_factor: float = 2.50,
        baseline_min_peak: float = 0.0020,
        baseline_min_exposure: float = 10.0,
        random_seed: int = 42,
        verbose: bool = True,
        progress_every_pct: float = 10.0,
    ):
        """
        Parametere
        ----------
        flow_model : CoastalThreeNetFlowModel
            Strømningsmodellen som leverer lokal hastighet u(x, y, t) for
            hvert punkt og tidspunkt. Endres denne, endres all pathogen-transport.

        dt_s : float, default 10.0
            Tidssteg i sekunder for partikkeloppdatering.
            - Lavere verdi gir jevnere og mer nøyaktig transport, men lengre kjøretid.
            - Høyere verdi gir raskere kjøring, men mer numerisk hopp mellom tidssteg.
            Typisk område: 5–30 s for denne raske screeningmodellen.

        total_time_s : float, default 1200.0
            Total simuleringstid i sekunder.
            Dette styrer hvor lenge patogener følges etter at de slippes inn oppstrøms.
            Øk denne hvis du vil studere sen ankomst, lang oppholdstid eller haleeffekter.

        particles_per_step : int, default 9
            Antall nye pathogen-partikler som slippes inn ved hvert tidssteg.
            Dette styrer oppløsningen på kilden oppstrøms:
            - Høyere verdi = glattere og mer stabil konsentrasjonskurve, men lengre kjøretid.
            - Lavere verdi = raskere kjøring, men mer hakkete signal og større samplingstøy.
            Merk at koden også tvinger inn eta=0 i innløpet for å sikre en partikkel på senterlinjen.

        source_load : float, default 1.0
            Relativ patogenkonsentrasjon for patogener i innløpet.
            Brukes til å beregne partikkelmasse som slippes inn per tidssteg.
            Hvis du dobler denne verdien, dobles all relativ masse/konsentrasjon i modellen.
            Enhet i denne koden er relativ/skalérbar, ikke kalibrert absolutt biomasse.

        diffusion_m2_s : float, default 0.12
            Turbulent diffusivitet i m²/s brukt i den stokastiske Brownsk-bevegelse-delen.
            - 0.0 gir ren adveksjon uten spredning.
            - Høyere verdi gir bredere og raskere lateral utspredelse av patogener.
            Påvirker særlig blanding rundt nøtene og hvor raskt plumen smøres ut.

        biology_enabled : bool, default True
            Slår enkel biologimodul av/på. Hvis False oppfører modellen seg i
            praksis som den gamle versjonen med bare adveksjon + diffusjon.

        base_inactivation_rate_1_s : float, default 5e-4
            Basis decay-rate [1/s] for avtagende levedyktighet / aktiv pathogen-risiko.
            Den aktive massen reduseres som exp(-k_eff * dt). Høyere verdi gir
            raskere tap av biologisk aktiv pathogen-masse.

        temperature_c : float, default 10.0
            Vanntemperatur [°C] brukt i enkel Q10-skalering av decay-raten.

        reference_temperature_c : float, default 10.0
            Referansetemperatur [°C] der temperaturfaktoren er lik 1.0.

        q10_inactivation : float, default 1.5
            Q10-faktor for temperaturfølsomheten til decay-raten.
            Eksempel: 1.5 betyr at k_eff øker med ca. 50 % for hver +10 °C.

        uv_inactivation_factor : float, default 1.0
            Dimensjonsløs lysfaktor som skalerer decay-raten direkte.
            1.0 = nøytral, >1 raskere tap av aktiv masse, <1 langsommere tap.

        species_infectivity_factor : float, default 1.0
            Dimensjonsløs arts-/toksisitetsfaktor som skalerer rapportert
            risikomasse og risikoeksponering. Transporten påvirkes ikke direkte.

        minimum_infectivity : float, default 1e-3
            Nedre terskel for levedyktighet. Partikler under denne terskelen
            deaktiveres for å spare regnetid.

        arrival_alarm_threshold_s : float, default 900.0
            Alarmterskel [s] for første ankomst til en nøt. Hvis patogener kommer
            raskere enn denne terskelen, heves et operativt ankomst-alarmflagg.

        exposure_alarm_threshold_mass_seconds : float, default 80.0
            Alarmterskel [relativ masse*s] for total risiko-vektet eksponering
            i en nøt. Brukes til enkelt varsel selv om samlet risikofarge ikke
            nødvendigvis er rød.

        yellow_arrival_threshold_s, red_arrival_threshold_s : float
            Gule/røde terskler [s] for hvor rask første ankomst må være for å
            bidra til gul eller rød risikostatus. Lavere tid = høyere risiko.

        yellow_peak_risk_concentration, red_peak_risk_concentration : float
            Gule/røde terskler for topp risiko-vektet relativ konsentrasjon
            inne i nøtene.

        yellow_exposure_threshold_mass_seconds, red_exposure_threshold_mass_seconds : float
            Gule/røde terskler for total risiko-vektet eksponering.

        no_arrival_means_green : bool, default True
            Hvis True gis grønne risikoflagg når ingen pathogen-partikler når en nøt
            i løpet av analyseperioden.

        random_seed : int, default 42
            Startverdi for tilfeldig generator brukt i diffusjonsleddet.
            Samme seed gir reproducerbare resultater ved samme øvrige parametere.
            Bytt denne hvis du vil teste følsomhet for stokastisk spredning.

        verbose : bool, default True
            Hvis True, skrives statusmeldinger ut mens analysen kjører.
            Anbefales i Spyder slik at brukeren ser at modellen jobber normalt.

        progress_every_pct : float, default 10.0
            Hvor ofte fremdrift skal skrives ut i prosent av total kjøretid per case.
            Eksempel: 10.0 skriver ut ved omtrent 10 %, 20 %, ..., 100 %.
            Lavere verdi gir tettere statusmeldinger.

        Praktisk pathogen-tolkning
        ---------------------
        - Vil du etterligne en sterkere patogenfront: øk ``source_load``.
        - Vil du etterligne mer urolig/mikset vann: øk ``diffusion_m2_s``.
        - Vil du ha finere tidsoppløsning: senk ``dt_s``.
        - Vil du la patogenfronten få mer tid til å passere hele anlegget: øk ``total_time_s``.
        - Vil du redusere numerisk støy i relative konsentrasjoner: øk ``particles_per_step``.
        - Vil du gi raskere biologisk avtagning: øk ``base_inactivation_rate_1_s``.
        - Vil du representere varmere vann: øk ``temperature_c``.
        - Vil du representere sterkere UV-inaktivering: øk ``uv_inactivation_factor``.
        - Vil du representere mer mer smittsom art: øk ``species_infectivity_factor``.
        - Vil du få tidligere alarm på raske ankomster: øk ``arrival_alarm_threshold_s``.
        - Vil du gjøre modellen mer konservativ: senk gule/røde terskler for konsentrasjon og eksponering.
        """
        if dt_s <= 0:
            raise ValueError('dt_s må være > 0 sekunder.')
        if total_time_s <= 0:
            raise ValueError('total_time_s må være > 0 sekunder.')
        if particles_per_step < 1:
            raise ValueError('particles_per_step må være minst 1.')
        if source_mode not in {'upstream_line', 'infected_net'}:
            raise ValueError("source_mode må være 'upstream_line' eller 'infected_net'.")
        if source_load < 0:
            raise ValueError('source_load kan ikke være negativ.')
        if shedding_rate_relative_per_s < 0:
            raise ValueError('shedding_rate_relative_per_s kan ikke være negativ.')
        if not (0.0 < source_patch_radius_fraction <= 1.0):
            raise ValueError('source_patch_radius_fraction må ligge i intervallet (0, 1].')
        if not (0.0 <= source_infectivity <= 1.0):
            raise ValueError('source_infectivity må ligge i intervallet [0, 1].')
        if diffusion_m2_s < 0:
            raise ValueError('diffusion_m2_s kan ikke være negativ.')
        if base_inactivation_rate_1_s < 0:
            raise ValueError('base_inactivation_rate_1_s kan ikke være negativ.')
        if q10_inactivation <= 0:
            raise ValueError('q10_inactivation må være > 0.')
        if uv_inactivation_factor < 0:
            raise ValueError('uv_inactivation_factor kan ikke være negativ.')
        if species_infectivity_factor < 0:
            raise ValueError('species_infectivity_factor kan ikke være negativ.')
        if not (0.0 <= minimum_infectivity <= 1.0):
            raise ValueError('minimum_infectivity må ligge i intervallet [0, 1].')
        for _name, _val in {
            'arrival_alarm_threshold_s': arrival_alarm_threshold_s,
            'exposure_alarm_threshold_mass_seconds': exposure_alarm_threshold_mass_seconds,
            'yellow_arrival_threshold_s': yellow_arrival_threshold_s,
            'yellow_peak_risk_concentration': yellow_peak_risk_concentration,
            'yellow_exposure_threshold_mass_seconds': yellow_exposure_threshold_mass_seconds,
            'red_arrival_threshold_s': red_arrival_threshold_s,
            'red_peak_risk_concentration': red_peak_risk_concentration,
            'red_exposure_threshold_mass_seconds': red_exposure_threshold_mass_seconds,
        }.items():
            if _val < 0:
                raise ValueError(f'{_name} kan ikke være negativ.')
        if red_arrival_threshold_s > yellow_arrival_threshold_s:
            raise ValueError('red_arrival_threshold_s bør være <= yellow_arrival_threshold_s.')
        if red_peak_risk_concentration < yellow_peak_risk_concentration:
            raise ValueError('red_peak_risk_concentration bør være >= yellow_peak_risk_concentration.')
        if red_exposure_threshold_mass_seconds < yellow_exposure_threshold_mass_seconds:
            raise ValueError('red_exposure_threshold_mass_seconds bør være >= yellow_exposure_threshold_mass_seconds.')
        if baseline_peak_reference not in {'max', 'mean'}:
            raise ValueError("baseline_peak_reference må være 'max' eller 'mean'.")
        if baseline_exposure_reference not in {'max', 'mean'}:
            raise ValueError("baseline_exposure_reference må være 'max' eller 'mean'.")
        for _name, _val in {
            'yellow_peak_factor': yellow_peak_factor,
            'red_peak_factor': red_peak_factor,
            'yellow_exposure_factor': yellow_exposure_factor,
            'red_exposure_factor': red_exposure_factor,
            'baseline_min_peak': baseline_min_peak,
            'baseline_min_exposure': baseline_min_exposure,
        }.items():
            if _val < 0:
                raise ValueError(f'{_name} kan ikke være negativ.')
        if red_peak_factor < yellow_peak_factor:
            raise ValueError('red_peak_factor bør være >= yellow_peak_factor.')
        if red_exposure_factor < yellow_exposure_factor:
            raise ValueError('red_exposure_factor bør være >= yellow_exposure_factor.')
        if progress_every_pct <= 0:
            raise ValueError('progress_every_pct må være > 0.')

        self.flow_model = flow_model
        self.dt_s = float(dt_s)
        self.total_time_s = float(total_time_s)
        self.particles_per_step = int(particles_per_step)
        self.pathogen_name = str(pathogen_name)
        self.source_mode = str(source_mode)
        self.source_net_name = source_net_name
        self.source_load = float(source_load)
        self.shedding_rate_relative_per_s = float(shedding_rate_relative_per_s)
        self.source_patch_radius_fraction = float(source_patch_radius_fraction)
        self.source_infectivity = float(source_infectivity)
        self.diffusion_m2_s = float(diffusion_m2_s)
        self.biology_enabled = bool(biology_enabled)
        self.base_inactivation_rate_1_s = float(base_inactivation_rate_1_s)
        self.temperature_c = float(temperature_c)
        self.reference_temperature_c = float(reference_temperature_c)
        self.q10_inactivation = float(q10_inactivation)
        self.uv_inactivation_factor = float(uv_inactivation_factor)
        self.species_infectivity_factor = float(species_infectivity_factor)
        self.vertical_preference_mode = str(vertical_preference_mode)
        self.minimum_infectivity = float(minimum_infectivity)
        self.arrival_alarm_threshold_s = float(arrival_alarm_threshold_s)
        self.exposure_alarm_threshold_mass_seconds = float(exposure_alarm_threshold_mass_seconds)
        self.yellow_arrival_threshold_s = float(yellow_arrival_threshold_s)
        self.yellow_peak_risk_concentration = float(yellow_peak_risk_concentration)
        self.yellow_exposure_threshold_mass_seconds = float(yellow_exposure_threshold_mass_seconds)
        self.red_arrival_threshold_s = float(red_arrival_threshold_s)
        self.red_peak_risk_concentration = float(red_peak_risk_concentration)
        self.red_exposure_threshold_mass_seconds = float(red_exposure_threshold_mass_seconds)
        self.no_arrival_means_green = bool(no_arrival_means_green)
        self.auto_calibrate_from_first_case = bool(auto_calibrate_from_first_case)
        self.baseline_case_name = str(baseline_case_name)
        self.baseline_peak_reference = str(baseline_peak_reference)
        self.baseline_exposure_reference = str(baseline_exposure_reference)
        self.yellow_peak_factor = float(yellow_peak_factor)
        self.red_peak_factor = float(red_peak_factor)
        self.yellow_exposure_factor = float(yellow_exposure_factor)
        self.red_exposure_factor = float(red_exposure_factor)
        self.baseline_min_peak = float(baseline_min_peak)
        self.baseline_min_exposure = float(baseline_min_exposure)
        self._risk_autocalibrated = False
        self._risk_baseline_info = {}
        self.random_seed = int(random_seed)
        self.rng = np.random.default_rng(self.random_seed)
        self.output_dir = self.flow_model.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = bool(verbose)
        self.progress_every_pct = float(progress_every_pct)
        self._run_start = time.perf_counter()

    def parameter_reference(self) -> dict:
        """
        Returnerer en oppslagsordbok med forklaring av sentrale pathogen-parametere.

        Kan brukes fra Spyder som:
            marcher.parameter_reference()
        eller:
            import pprint; pprint.pp(marcher.parameter_reference())
        """
        return {
            'dt_s': 'Tidssteg [s]. Lavere = mer nøyaktig og tregere. Høyere = raskere og grovere.',
            'total_time_s': 'Total simuleringstid [s]. Øk for å fange sen ankomst og lang hale.',
            'particles_per_step': 'Antall nye partikler per tidssteg. Høyere = glattere konsentrasjon og lengre kjøretid.',
            'pathogen_name': 'Navn på patogenet som analyseres.',
            'source_mode': "Kildemodus: 'upstream_line' eller 'infected_net'.",
            'source_net_name': 'Navn på infisert nøt når source_mode=infected_net.',
            'source_load': 'Relativ kildekonsentrasjon for upstream_line-kilde. Skalerer all relativ konsentrasjon opp/ned.',
            'shedding_rate_relative_per_s': 'Relativ utskillingsrate [masse/s] fra infisert nøt.',
            'source_patch_radius_fraction': 'Fraksjon av nettradius som brukes som lokalt utslippsområde.',
            'source_infectivity': 'Initial infektivitet [0,1] for nye partikler ved kilden.',
            'diffusion_m2_s': 'Turbulent diffusivitet [m²/s]. Øker lateral spredning og miksing.',
            'biology_enabled': 'Slår enkel biologimodul for avtagende levedyktighet av/på.',
            'base_inactivation_rate_1_s': 'Basisrate [1/s] for tap av aktiv pathogen-masse.',
            'temperature_c': 'Vanntemperatur [°C] brukt i Q10-skalering av decay-raten.',
            'reference_temperature_c': 'Referansetemperatur [°C] der temperaturfaktor = 1.0.',
            'q10_inactivation': 'Q10-faktor for temperaturfølsomhet i decay-raten.',
            'uv_inactivation_factor': 'Dimensjonsløs skaleringsfaktor for UV-inaktivering på decay-raten.',
            'species_infectivity_factor': 'Dimensjonsløs faktor som skalerer risikomasse og risikoeksponering.',
            'vertical_preference_mode': 'Placeholder for senere 2.5D/3D-utvidelse.',
            'minimum_infectivity': 'Partikler under denne infectivity terskelen fjernes for å spare regnetid.',
            'arrival_alarm_threshold_s': 'Alarmterskel [s] for rask første ankomst til en nøt.',
            'exposure_alarm_threshold_mass_seconds': 'Alarmterskel [relativ masse*s] for total risiko-vektet eksponering.',
            'yellow_arrival_threshold_s': 'Gul terskel [s] for første ankomst.',
            'yellow_peak_risk_concentration': 'Gul terskel for topp risiko-vektet relativ konsentrasjon.',
            'yellow_exposure_threshold_mass_seconds': 'Gul terskel for total risiko-vektet eksponering.',
            'red_arrival_threshold_s': 'Rød terskel [s] for første ankomst.',
            'red_peak_risk_concentration': 'Rød terskel for topp risiko-vektet relativ konsentrasjon.',
            'red_exposure_threshold_mass_seconds': 'Rød terskel for total risiko-vektet eksponering.',
            'no_arrival_means_green': 'Hvis True gir manglende ankomst grønn status.',
            'auto_calibrate_from_first_case': 'Hvis True kalibreres peak-/eksponeringsterskler fra første baseline-case.',
            'baseline_case_name': 'Navn på case som skal brukes som baseline, typisk langs.',
            'baseline_peak_reference': "Bruk 'max' eller 'mean' som baseline for peak risk concentration.",
            'baseline_exposure_reference': "Bruk 'max' eller 'mean' som baseline for eksponering.",
            'yellow_peak_factor': 'Gul peak-terskel = baseline_peak * denne faktoren.',
            'red_peak_factor': 'Rød peak-terskel = baseline_peak * denne faktoren.',
            'yellow_exposure_factor': 'Gul eksponeringsterskel = baseline_exposure * denne faktoren.',
            'red_exposure_factor': 'Rød eksponeringsterskel = baseline_exposure * denne faktoren.',
            'baseline_min_peak': 'Nedre gulvverdi for baseline peak før faktorer brukes.',
            'baseline_min_exposure': 'Nedre gulvverdi for baseline exposure før faktorer brukes.',
            'random_seed': 'Seed for tilfeldig diffusjon. Samme seed gir reproducerbar kjøring.',
            'verbose': 'Skrur statusmeldinger av/på under kjøring.',
            'progress_every_pct': 'Hvor ofte fremdrift skrives ut i prosent per case.',
        }

    def _temperature_factor(self) -> float:
        return self.q10_inactivation ** ((self.temperature_c - self.reference_temperature_c) / 10.0)

    def effective_inactivation_rate_1_s(self) -> float:
        if not self.biology_enabled:
            return 0.0
        return max(0.0, self.base_inactivation_rate_1_s * self._temperature_factor() * self.uv_inactivation_factor)

    def _infectious_mass(self, p: pathogenParticle) -> float:
        return p.mass * max(0.0, min(1.0, p.infectivity))

    def _risk_mass(self, p: pathogenParticle) -> float:
        return self._infectious_mass(p) * self.species_infectivity_factor

    def _risk_action(self, status: str) -> str:
        actions = {
            'GREEN': 'Fortsett normal overvåking og rutinemessig prøvetaking.',
            'YELLOW': 'Øk prøvetaking og følg utviklingen tett. Vurder driftsjusteringer og ekstra varsling.',
            'RED': 'Utløs alarm, varsle drift umiddelbart og vurder strakstiltak for å redusere eksponering.',
        }
        return actions.get(status.upper(), 'Ingen anbefalt handling definert.')


    def _derive_baseline_value(self, values: pd.Series, mode: str, minimum: float) -> float:
        vals = pd.to_numeric(values, errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
        if vals.empty:
            return float(minimum)
        if mode == 'mean':
            return float(max(minimum, vals.mean()))
        return float(max(minimum, vals.max()))

    def _apply_auto_risk_calibration(self, baseline_summary: pd.DataFrame, baseline_case_name: str | None = None) -> None:
        if not self.auto_calibrate_from_first_case or baseline_summary is None or baseline_summary.empty:
            return
        baseline_summary = self._standardize_summary_df(baseline_summary)
        case_name = baseline_case_name or self.baseline_case_name

        old_thresholds = {
            'yellow_peak_risk_concentration': float(self.yellow_peak_risk_concentration),
            'red_peak_risk_concentration': float(self.red_peak_risk_concentration),
            'yellow_exposure_threshold_mass_seconds': float(self.yellow_exposure_threshold_mass_seconds),
            'red_exposure_threshold_mass_seconds': float(self.red_exposure_threshold_mass_seconds),
            'exposure_alarm_threshold_mass_seconds': float(self.exposure_alarm_threshold_mass_seconds),
        }

        peak_baseline = self._derive_baseline_value(
            baseline_summary['peak_relative_risk_concentration'],
            self.baseline_peak_reference,
            self.baseline_min_peak,
        )
        exposure_baseline = self._derive_baseline_value(
            baseline_summary['total_risk_exposure_mass_seconds'],
            self.baseline_exposure_reference,
            self.baseline_min_exposure,
        )

        self.yellow_peak_risk_concentration = float(peak_baseline * self.yellow_peak_factor)
        self.red_peak_risk_concentration = float(peak_baseline * self.red_peak_factor)
        self.yellow_exposure_threshold_mass_seconds = float(exposure_baseline * self.yellow_exposure_factor)
        self.red_exposure_threshold_mass_seconds = float(exposure_baseline * self.red_exposure_factor)
        self.exposure_alarm_threshold_mass_seconds = float(self.red_exposure_threshold_mass_seconds)
        self._risk_autocalibrated = True
        self._risk_thresholds_before_autocalibration = old_thresholds
        self._risk_baseline_info = {
            'baseline_case_name': case_name,
            'peak_baseline': peak_baseline,
            'exposure_baseline': exposure_baseline,
            'baseline_peak_reference': self.baseline_peak_reference,
            'baseline_exposure_reference': self.baseline_exposure_reference,
            'yellow_peak_factor': self.yellow_peak_factor,
            'red_peak_factor': self.red_peak_factor,
            'yellow_exposure_factor': self.yellow_exposure_factor,
            'red_exposure_factor': self.red_exposure_factor,
            'yellow_peak_risk_concentration': self.yellow_peak_risk_concentration,
            'red_peak_risk_concentration': self.red_peak_risk_concentration,
            'yellow_exposure_threshold_mass_seconds': self.yellow_exposure_threshold_mass_seconds,
            'red_exposure_threshold_mass_seconds': self.red_exposure_threshold_mass_seconds,
            'exposure_alarm_threshold_mass_seconds': self.exposure_alarm_threshold_mass_seconds,
            'previous_thresholds': old_thresholds,
        }
        self._log(
            "Auto-kalibrerte risikoterskler fra baseline-case "
            f"'{case_name}': peak_baseline={peak_baseline:.4f} -> yellow/red peak="
            f"{self.yellow_peak_risk_concentration:.4f}/{self.red_peak_risk_concentration:.4f}, "
            f"exposure_baseline={exposure_baseline:.2f} -> yellow/red exposure="
            f"{self.yellow_exposure_threshold_mass_seconds:.2f}/{self.red_exposure_threshold_mass_seconds:.2f}"
        )
        self._log_auto_risk_calibration_summary()


    def _log_auto_risk_calibration_summary(self) -> None:
        if not self._risk_autocalibrated or not self._risk_baseline_info:
            return
        old = self._risk_thresholds_before_autocalibration or {}
        info = self._risk_baseline_info
        self._log("Risikokalibrering – baseline og terskeloppdatering:")
        self._log(
            f"  Baseline-case: {info.get('baseline_case_name', self.baseline_case_name)} | "
            f"peak baseline={float(info.get('peak_baseline', 0.0)):.4f} "
            f"({info.get('baseline_peak_reference', self.baseline_peak_reference)}) | "
            f"exposure baseline={float(info.get('exposure_baseline', 0.0)):.2f} "
            f"({info.get('baseline_exposure_reference', self.baseline_exposure_reference)})"
        )
        self._log(
            f"  Peak terskler: gul {old.get('yellow_peak_risk_concentration', float('nan')):.4f} -> {self.yellow_peak_risk_concentration:.4f} | "
            f"rød {old.get('red_peak_risk_concentration', float('nan')):.4f} -> {self.red_peak_risk_concentration:.4f}"
        )
        self._log(
            f"  Exposure terskler: gul {old.get('yellow_exposure_threshold_mass_seconds', float('nan')):.2f} -> {self.yellow_exposure_threshold_mass_seconds:.2f} | "
            f"rød {old.get('red_exposure_threshold_mass_seconds', float('nan')):.2f} -> {self.red_exposure_threshold_mass_seconds:.2f} | "
            f"alarm {old.get('exposure_alarm_threshold_mass_seconds', float('nan')):.2f} -> {self.exposure_alarm_threshold_mass_seconds:.2f}"
        )
        self._log(
            f"  Faktorer: peak gul/rød = {self.yellow_peak_factor:.2f}/{self.red_peak_factor:.2f} | "
            f"exposure gul/rød = {self.yellow_exposure_factor:.2f}/{self.red_exposure_factor:.2f}"
        )

    def _reclassify_summary_df(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        summary_df = self._standardize_summary_df(summary_df).copy()
        if summary_df.empty:
            return summary_df
        new_rows = []
        for _, row in summary_df.iterrows():
            first_arrival_s = row.get('first_arrival_s', np.nan)
            if pd.isna(first_arrival_s):
                first_arrival_s = None
            peak_risk_conc = float(row.get('peak_relative_risk_concentration', 0.0) or 0.0)
            total_risk_exposure = float(row.get('total_risk_exposure_mass_seconds', 0.0) or 0.0)
            status, reasons, arrival_alarm, exposure_alarm = self._classify_risk_status(
                first_arrival_s, peak_risk_conc, total_risk_exposure
            )
            row = row.copy()
            row['risk_status'] = status
            row['risk_reasons'] = '; '.join(reasons)
            row['arrival_alarm'] = bool(arrival_alarm)
            row['exposure_alarm'] = bool(exposure_alarm)
            row['operational_alarm'] = bool(arrival_alarm or exposure_alarm or status == 'RED')
            row['recommended_action'] = self._risk_action(status)
            new_rows.append(row)
        return pd.DataFrame(new_rows)

    def _classify_risk_status(
        self,
        first_arrival_s: float | None,
        peak_risk_conc: float,
        total_risk_exposure: float,
    ) -> tuple[str, list[str], bool, bool]:
        reasons: list[str] = []
        no_arrival = first_arrival_s is None or (isinstance(first_arrival_s, float) and np.isnan(first_arrival_s))

        if no_arrival and self.no_arrival_means_green and peak_risk_conc <= 0 and total_risk_exposure <= 0:
            return 'GREEN', ['Ingen registrert ankomst i analyseperioden.'], False, False

        arrival_alarm = (not no_arrival) and (first_arrival_s <= self.arrival_alarm_threshold_s)
        exposure_alarm = total_risk_exposure >= self.exposure_alarm_threshold_mass_seconds

        is_red = False
        if (not no_arrival) and (first_arrival_s <= self.red_arrival_threshold_s):
            is_red = True
            reasons.append(f'Rask ankomst: {first_arrival_s:.0f} s <= rød terskel {self.red_arrival_threshold_s:.0f} s')
        elif (not no_arrival) and (first_arrival_s <= self.yellow_arrival_threshold_s):
            reasons.append(f'Tidlig ankomst: {first_arrival_s:.0f} s <= gul terskel {self.yellow_arrival_threshold_s:.0f} s')

        if peak_risk_conc >= self.red_peak_risk_concentration:
            is_red = True
            reasons.append(f'Høy topp-konsentrasjon: {peak_risk_conc:.4f} >= rød terskel {self.red_peak_risk_concentration:.4f}')
        elif peak_risk_conc >= self.yellow_peak_risk_concentration:
            reasons.append(f'Moderat/høy topp-konsentrasjon: {peak_risk_conc:.4f} >= gul terskel {self.yellow_peak_risk_concentration:.4f}')

        if total_risk_exposure >= self.red_exposure_threshold_mass_seconds:
            is_red = True
            reasons.append(f'Høy total eksponering: {total_risk_exposure:.2f} >= rød terskel {self.red_exposure_threshold_mass_seconds:.2f}')
        elif total_risk_exposure >= self.yellow_exposure_threshold_mass_seconds:
            reasons.append(f'Økt total eksponering: {total_risk_exposure:.2f} >= gul terskel {self.yellow_exposure_threshold_mass_seconds:.2f}')

        if is_red:
            status = 'RED'
        elif reasons:
            status = 'YELLOW'
        else:
            status = 'GREEN'
            reasons.append('Alle operative terskler ligger under gule alarmgrenser.')

        return status, reasons, arrival_alarm, exposure_alarm

    def _apply_biology_step(self, p: pathogenParticle) -> None:
        if not self.biology_enabled or not p.alive:
            return
        k_eff = self.effective_inactivation_rate_1_s()
        if k_eff > 0.0:
            p.infectivity *= math.exp(-k_eff * self.dt_s)
            p.infectivity = max(0.0, min(1.0, p.infectivity))
        if p.infectivity < self.minimum_infectivity:
            p.alive = False

    def _log_parameter_summary(self) -> None:
        """Skriv ut en kort, brukervennlig oppsummering av pathogen-parameterne."""
        self._log('pathogen-parameteroppsett:')
        self._log(f"  dt_s={self.dt_s:.2f} s -> tidsoppløsning for partikkeloppdatering")
        self._log(f"  total_time_s={self.total_time_s:.1f} s -> total simuleringstid")
        self._log(f"  pathogen_name={self.pathogen_name}")
        self._log(f"  particles_per_step={self.particles_per_step} -> nye partikler per tidssteg")
        self._log(f"  source_mode={self.source_mode}")
        if self.source_mode == 'upstream_line':
            self._log(f"  source_load={self.source_load:.4g} -> relativ patogenkonsentrasjon i innløpet")
            self._log("  regional upstream-kilde plasseres automatisk på åpen sjø-side, ikke ved kystlinjen")
        else:
            self._log(f"  source_net_name={self._resolve_source_net().name} -> infisert kilde-nøt")
            self._log(f"  shedding_rate_relative_per_s={self.shedding_rate_relative_per_s:.4g} masse/s")
            self._log(f"  source_patch_radius_fraction={self.source_patch_radius_fraction:.3f}")
        self._log(f"  source_infectivity={self.source_infectivity:.3f} -> initial infektivitet ved kilde")
        self._log(f"  diffusion_m2_s={self.diffusion_m2_s:.4g} m²/s -> stokastisk spredning/miksing")
        self._log(f"  biology_enabled={self.biology_enabled} | base_inactivation_rate_1_s={self.base_inactivation_rate_1_s:.4g} 1/s")
        self._log(f"  temperature_c={self.temperature_c:.2f} °C | reference_temperature_c={self.reference_temperature_c:.2f} °C | q10_inactivation={self.q10_inactivation:.3f}")
        self._log(f"  uv_inactivation_factor={self.uv_inactivation_factor:.3f} | species_infectivity_factor={self.species_infectivity_factor:.3f} | vertical_preference_mode={self.vertical_preference_mode} | minimum_infectivity={self.minimum_infectivity:.4g}")
        self._log(f"  effective_inactivation_rate_1_s={self.effective_inactivation_rate_1_s():.4g} 1/s")
        self._log(f"  risk auto-calibration={self.auto_calibrate_from_first_case} | baseline_case_name={self.baseline_case_name}")
        if self.auto_calibrate_from_first_case:
            self._log(
                f"  baseline refs: peak={self.baseline_peak_reference}, exposure={self.baseline_exposure_reference} | "
                f"peak factors yellow/red={self.yellow_peak_factor:.2f}/{self.red_peak_factor:.2f} | "
                f"exposure factors yellow/red={self.yellow_exposure_factor:.2f}/{self.red_exposure_factor:.2f}"
            )
        self._log(f"  random_seed={self.random_seed} -> reproducerbar diffusjonsstøy")
        self._log(f"  verbose={self.verbose} | progress_every_pct={self.progress_every_pct:.1f}%")

    def _log(self, message: str) -> None:
        if self.verbose:
            elapsed = time.perf_counter() - self._run_start
            print(f"[AquaGuard +{elapsed:7.1f}s] {message}", flush=True)

    def _inlet_line(self, case_dir: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Beregn oppstrøms innløpslinje for regional patogenkilde.

        For 'upstream_line' skal kilden representere regional innstrømning utenfra,
        altså fra åpen sjø-side og ikke fra kystlinjen. Derfor legges det inn en
        sikkerhetssjekk som snur retningen dersom case_dir peker bort fra kysten
        (positiv projeksjon på kystnormalen).
        """
        e = self.flow_model._unit(case_dir)
        coast_normal = np.array([0.0, 1.0])  # peker fra kystlinjen og utover i domenet
        flipped_for_open_sea = False
        if float(np.dot(e, coast_normal)) > 0.0:
            e = -e
            flipped_for_open_sea = True
        ep = np.array([-e[1], e[0]])
        corners = np.array([
            [self.flow_model.domain['x'][0], self.flow_model.domain['y'][0]],
            [self.flow_model.domain['x'][0], self.flow_model.domain['y'][1]],
            [self.flow_model.domain['x'][1], self.flow_model.domain['y'][0]],
            [self.flow_model.domain['x'][1], self.flow_model.domain['y'][1]],
        ])
        s_vals = corners @ e
        eta_vals = corners @ ep
        s_min = float(np.min(s_vals)) - 15.0
        eta_min = float(np.min(eta_vals)) + 15.0
        eta_max = float(np.max(eta_vals)) - 15.0
        origin = s_min * e
        if self.verbose:
            y_source = float(origin[1])
            boundary_label = 'åpen sjø-side' if y_source > self.flow_model.coast.y_coast + 20.0 else 'kystsiden/nær land'
            msg = f"Regional kilde legges på {boundary_label}: origin=({origin[0]:.1f}, {origin[1]:.1f}) m"
            if flipped_for_open_sea:
                msg += ' | case_dir ble snudd for å sikre åpen rand.'
            self._log(msg)
        return origin, ep, np.array([eta_min, eta_max])

    def _resolve_source_net(self) -> Net:
        if self.source_net_name is None:
            return self.flow_model.nets[0]
        for net in self.flow_model.nets:
            if net.name == self.source_net_name:
                return net
        raise ValueError(f"Fant ikke source_net_name={self.source_net_name!r} blant {[n.name for n in self.flow_model.nets]}")

    def _spawn_particles(self, particles: List[pathogenParticle], current_t: float, case_name: str) -> int:
        added = 0
        if self.source_mode == 'upstream_line':
            case_dir = self.flow_model.case_vector(case_name)
            origin, ep, eta_range = self._inlet_line(case_dir)
            width = eta_range[1] - eta_range[0]
            if self.particles_per_step <= 1:
                etas = np.array([(eta_range[0] + eta_range[1]) / 2.0])
            else:
                etas = np.linspace(eta_range[0], eta_range[1], self.particles_per_step)
                etas = np.unique(np.concatenate([etas, np.array([0.0])]))
            mass_per_particle = self.source_load * width / max(len(etas), 1)
            for eta in etas:
                p = origin + eta * ep
                if p[1] < self.flow_model.coast.y_coast + 2.0:
                    p[1] = self.flow_model.coast.y_coast + 2.0
                particles.append(
                    pathogenParticle(
                        x=float(p[0]), y=float(p[1]), mass=float(mass_per_particle),
                        birth_time_s=float(current_t), infectivity=float(self.source_infectivity),
                        entered_once={net.name: False for net in self.flow_model.nets},
                        exposure_s={net.name: 0.0 for net in self.flow_model.nets},
                    )
                )
                added += 1
            return added

        source_net = self._resolve_source_net()
        patch_radius = max(0.5, self.source_patch_radius_fraction * source_net.radius)
        total_mass = self.shedding_rate_relative_per_s * self.dt_s
        mass_per_particle = total_mass / max(self.particles_per_step, 1)
        for i in range(self.particles_per_step):
            if i == 0:
                r = 0.0
                theta = 0.0
            else:
                r = patch_radius * np.sqrt(self.rng.uniform(0.0, 1.0))
                theta = self.rng.uniform(0.0, 2.0 * np.pi)
            x = source_net.center[0] + r * np.cos(theta)
            y = source_net.center[1] + r * np.sin(theta)
            if y < self.flow_model.coast.y_coast + 2.0:
                y = self.flow_model.coast.y_coast + 2.0
            particles.append(
                pathogenParticle(
                    x=float(x), y=float(y), mass=float(mass_per_particle),
                    birth_time_s=float(current_t), infectivity=float(self.source_infectivity),
                    entered_once={net.name: False for net in self.flow_model.nets},
                    exposure_s={net.name: 0.0 for net in self.flow_model.nets},
                )
            )
            added += 1
        return added

    def _inside_domain(self, x: float, y: float) -> bool:
        x_min, x_max = self.flow_model.domain['x']
        y_min, y_max = self.flow_model.domain['y']
        pad = 60.0
        return (x_min - pad <= x <= x_max + pad) and (y_min - 1.0 <= y <= y_max + pad)

    def _reflect_off_coast(self, p: pathogenParticle) -> None:
        y0 = self.flow_model.coast.y_coast
        if p.y < y0:
            p.y = 2.0 * y0 - p.y

    def _crossed_into_impermeable_net(self, x_old: float, y_old: float, x_new: float, y_new: float) -> Optional[Net]:
        """
        Returnerer noten dersom en partikkel krysser fra utsiden til innsiden av en
        helt tett not i dette tidssteget.

        I v1.21 brukes dette for å hindre at partikler lekker inn i en tett not
        via diffusjon eller store tidssteg.
        """
        for net in self.flow_model.nets:
            if not net.is_impermeable:
                continue
            was_inside = self.flow_model._point_inside_net(x_old, y_old, net)
            is_inside = self.flow_model._point_inside_net(x_new, y_new, net)
            if (not was_inside) and is_inside:
                return net
        return None

    def _push_outside_impermeable_net(self, x_old: float, y_old: float, x_new: float, y_new: float, net: Net) -> Tuple[float, float]:
        """
        Flytter et foreslått nytt punkt tilbake til utsiden av en tett not.

        Strategi:
        1. Hvis forrige punkt var utenfor, bruk dette som basis.
        2. Prosjiser punktet til nærmeste punkt på sirkelgrensen.
        3. Flytt det en liten epsilon utover langs normalretningen.
        """
        cx, cy = net.center
        base_x, base_y = (x_old, y_old) if not self.flow_model._point_inside_net(x_old, y_old, net) else (x_new, y_new)
        dx = base_x - cx
        dy = base_y - cy
        r = math.hypot(dx, dy)
        if r < 1e-12:
            dx, dy, r = 1.0, 0.0, 1.0
        ux, uy = dx / r, dy / r
        eps = max(0.05, 1.0e-3 * net.radius)
        return cx + (net.radius + eps) * ux, cy + (net.radius + eps) * uy

    def run_case(self, case_name: str) -> dict:
        case_start = time.perf_counter()
        particles: List[pathogenParticle] = []
        times = np.arange(0.0, self.total_time_s + self.dt_s, self.dt_s)
        total_steps = len(times)
        first_arrival_s = {net.name: None for net in self.flow_model.nets}
        concentration_ts = {net.name: [] for net in self.flow_model.nets}
        risk_concentration_ts = {net.name: [] for net in self.flow_model.nets}
        inside_count_ts = {net.name: [] for net in self.flow_model.nets}
        mean_infectivity_ts = {net.name: [] for net in self.flow_model.nets}
        total_exposure_particle_seconds = {net.name: 0.0 for net in self.flow_model.nets}
        total_risk_exposure_mass_seconds = {net.name: 0.0 for net in self.flow_model.nets}
        snapshots = {}
        snapshot_times = [0, 200, 400, 600, 800, 1000, 1200]
        snapshot_indices = {int(round(t / self.dt_s)) for t in snapshot_times}
        last_announced_pct = -1.0

        self._log(
            f"Starter case '{case_name}' med {total_steps} tidssteg, dt={self.dt_s:.1f} s, "
            f"particles_per_step={self.particles_per_step}, k_eff={self.effective_inactivation_rate_1_s():.4g} 1/s."
        )

        for it, t in enumerate(times):
            spawned_now = self._spawn_particles(particles, t, case_name)
            case_dir = self.flow_model.case_vector(case_name)
            alive_before = sum(1 for p in particles if p.alive)

            for p in particles:
                if not p.alive:
                    continue
                x_old, y_old = p.x, p.y
                v = self.flow_model.velocity_at_point_time(p.x, p.y, t, case_dir)
                if self.diffusion_m2_s > 0.0:
                    sigma = math.sqrt(2.0 * self.diffusion_m2_s * self.dt_s)
                    dx_diff, dy_diff = self.rng.normal(0.0, sigma, size=2)
                else:
                    dx_diff, dy_diff = 0.0, 0.0
                x_new = float(p.x + v[0] * self.dt_s + dx_diff)
                y_new = float(p.y + v[1] * self.dt_s + dy_diff)

                crossed_net = self._crossed_into_impermeable_net(x_old, y_old, x_new, y_new)
                if crossed_net is not None:
                    x_new, y_new = self._push_outside_impermeable_net(x_old, y_old, x_new, y_new, crossed_net)

                p.x, p.y = x_new, y_new
                self._reflect_off_coast(p)

                # Sikkerhetsnett: tillat aldri aktive partikler å ende inne i en tett not.
                for tight_net in self.flow_model.nets:
                    if tight_net.is_impermeable and self.flow_model._point_inside_net(p.x, p.y, tight_net):
                        p.x, p.y = self._push_outside_impermeable_net(x_old, y_old, p.x, p.y, tight_net)

                if not self._inside_domain(p.x, p.y):
                    p.alive = False
                    continue

                self._apply_biology_step(p)
                if not p.alive:
                    continue

                for net in self.flow_model.nets:
                    inside = self.flow_model._point_inside_net(p.x, p.y, net)
                    if inside:
                        if not p.entered_once[net.name]:
                            p.entered_once[net.name] = True
                            if first_arrival_s[net.name] is None:
                                first_arrival_s[net.name] = t + self.dt_s
                                self._log(f"  Første ankomst i {net.name} for case '{case_name}' ved t={t + self.dt_s:.0f} s.")
                        p.exposure_s[net.name] += self.dt_s
                        total_exposure_particle_seconds[net.name] += self._infectious_mass(p) * self.dt_s
                        total_risk_exposure_mass_seconds[net.name] += self._risk_mass(p) * self.dt_s

            for net in self.flow_model.nets:
                inside_particles = [p for p in particles if p.alive and self.flow_model._point_inside_net(p.x, p.y, net)]
                total_infectious_mass_inside = sum(self._infectious_mass(p) for p in inside_particles)
                total_risk_mass_inside = sum(self._risk_mass(p) for p in inside_particles)
                concentration_rel = total_infectious_mass_inside / net.plan_area
                risk_concentration_rel = total_risk_mass_inside / net.plan_area
                mean_infectivity = float(np.mean([p.infectivity for p in inside_particles])) if inside_particles else float('nan')
                concentration_ts[net.name].append(concentration_rel)
                risk_concentration_ts[net.name].append(risk_concentration_rel)
                inside_count_ts[net.name].append(len(inside_particles))
                mean_infectivity_ts[net.name].append(mean_infectivity)

            if it in snapshot_indices:
                alive_xy = np.array([[p.x, p.y] for p in particles if p.alive], dtype=float)
                alive_mass = np.array([self._infectious_mass(p) for p in particles if p.alive], dtype=float)
                alive_risk_mass = np.array([self._risk_mass(p) for p in particles if p.alive], dtype=float)
                snapshots[int(round(t))] = {'xy': alive_xy, 'mass': alive_mass, 'risk_mass': alive_risk_mass}
                self._log(f"  Snapshot lagret i minne for case '{case_name}' ved t={t:.0f} s med {len(alive_xy)} aktive partikler.")

            pct = 100.0 * (it + 1) / total_steps
            if pct >= last_announced_pct + self.progress_every_pct or it == total_steps - 1:
                alive_after = sum(1 for p in particles if p.alive)
                peak_now = max(concentration_ts[net.name][-1] for net in self.flow_model.nets)
                mean_infectivity_all = float(np.mean([p.infectivity for p in particles if p.alive])) if alive_after > 0 else float('nan')
                self._log(
                    f"  Fremdrift '{case_name}': {pct:5.1f}% | t={t:6.1f} s | nye={spawned_now:3d} | "
                    f"aktive før/etter={alive_before:4d}/{alive_after:4d} | peak active pathogen conc nå={peak_now:.4f} | "
                    f"mean infectivity={mean_infectivity_all:.3f}"
                )
                last_announced_pct = pct

        summary_rows = []
        k_eff = self.effective_inactivation_rate_1_s()
        temp_factor = self._temperature_factor()
        for net in self.flow_model.nets:
            entered_particles = [p for p in particles if p.exposure_s[net.name] > 0.0]
            mean_residence = float(np.mean([p.exposure_s[net.name] for p in entered_particles])) if entered_particles else float('nan')
            max_residence = float(np.max([p.exposure_s[net.name] for p in entered_particles])) if entered_particles else float('nan')
            mean_infectivity_entered = float(np.mean([p.infectivity for p in entered_particles])) if entered_particles else float('nan')
            peak_rel = float(np.max(concentration_ts[net.name])) if concentration_ts[net.name] else 0.0
            mean_rel = float(np.mean(concentration_ts[net.name])) if concentration_ts[net.name] else 0.0
            peak_risk_rel = float(np.max(risk_concentration_ts[net.name])) if risk_concentration_ts[net.name] else 0.0
            mean_risk_rel = float(np.mean(risk_concentration_ts[net.name])) if risk_concentration_ts[net.name] else 0.0
            total_exp = float(total_exposure_particle_seconds[net.name])
            total_risk_exp = float(total_risk_exposure_mass_seconds[net.name])
            status, reasons, arrival_alarm, exposure_alarm = self._classify_risk_status(
                first_arrival_s[net.name], peak_risk_rel, total_risk_exp
            )
            action = self._risk_action(status)
            if status in ('YELLOW', 'RED') or arrival_alarm or exposure_alarm:
                self._log(
                    f"  Risk {status} i {net.name} ({case_name}) | arrival_alarm={arrival_alarm} | exposure_alarm={exposure_alarm} | "
                    f"årsaker: {'; '.join(reasons)}"
                )
            summary_rows.append({
                'case_name': case_name,
                'direction': case_name,
                'net': net.name,
                'soliditet': net.solidity,
                'beta_1screen': net.beta,
                'beta_2screens': net.beta2,
                'biology_enabled': self.biology_enabled,
                'base_inactivation_rate_1_s': self.base_inactivation_rate_1_s,
                'effective_inactivation_rate_1_s': k_eff,
                'temperature_c': self.temperature_c,
                'temperature_factor': temp_factor,
                'uv_inactivation_factor': self.uv_inactivation_factor,
                'species_infectivity_factor': self.species_infectivity_factor,
                'first_arrival_s': first_arrival_s[net.name],
                'first_arrival_min': None if first_arrival_s[net.name] is None else first_arrival_s[net.name] / 60.0,
                'mean_residence_s': mean_residence,
                'max_residence_s': max_residence,
                'mean_infectivity_of_entered_particles': mean_infectivity_entered,
                'peak_relative_concentration': peak_rel,
                'mean_relative_concentration': mean_rel,
                'peak_relative_risk_concentration': peak_risk_rel,
                'mean_relative_risk_concentration': mean_risk_rel,
                'total_exposure_mass_seconds': total_exp,
                'total_risk_exposure_mass_seconds': total_risk_exp,
                'risk_status': status,
                'recommended_action': action,
                'risk_reasons': ' | '.join(reasons),
                'arrival_alarm': bool(arrival_alarm),
                'exposure_alarm': bool(exposure_alarm),
                'operational_alarm': bool(arrival_alarm or exposure_alarm or status == 'RED'),
            })

        time_series_df = pd.DataFrame({'time_s': times})
        for net in self.flow_model.nets:
            safe = net.name.lower().replace(' ', '_')
            time_series_df[f'{safe}_conc_rel'] = concentration_ts[net.name]
            time_series_df[f'{safe}_risk_conc_rel'] = risk_concentration_ts[net.name]
            time_series_df[f'{safe}_inside_count'] = inside_count_ts[net.name]
            time_series_df[f'{safe}_mean_infectivity'] = mean_infectivity_ts[net.name]

        case_elapsed = time.perf_counter() - case_start
        self._log(f"Case '{case_name}' ferdig på {case_elapsed:.1f} s.")

        return {
            'case_name': case_name,
            'times': times,
            'time_series': time_series_df,
            'summary': pd.DataFrame(summary_rows),
            'snapshots': snapshots,
        }

    def render_snapshot_grid(self, case_result: dict, filename: str) -> Path:
        sample_times = [0, 200, 400, 600, 800, 1000, 1200]
        self._log(f"Renderer snapshot-grid for '{case_result['case_name']}' -> {filename}")
        fig, axes = plt.subplots(2, 4, figsize=(17.5, 8.8), constrained_layout=True)
        axes = axes.flatten()
        for idx, (ax, t_s) in enumerate(zip(axes, sample_times), start=1):
            self._log(f"  Beregner felt {idx}/{len(sample_times)} for '{case_result['case_name']}' ved t={t_s} s")
            field = self.flow_model.evaluate_field(case_result['case_name'], t_s, nx=111, ny=81)
            X, Y, U, V = field['X'], field['Y'], field['U'], field['V']
            speed = np.where(np.isfinite(field['speed']), field['speed'], np.nan)
            finite_speed = speed[np.isfinite(speed)]
            levels = np.linspace(float(np.nanmin(finite_speed)), float(np.nanmax(finite_speed)), 22)
            ax.contourf(X, Y, speed, levels=levels, cmap='viridis', alpha=0.78)
            ax.streamplot(X[0, :], Y[:, 0], np.nan_to_num(U), np.nan_to_num(V), color='white', density=1.2, linewidth=0.55, arrowsize=0.7)
            snap = case_result['snapshots'].get(t_s, {'xy': np.empty((0, 2)), 'mass': np.empty((0,)), 'risk_mass': np.empty((0,))})
            xy = snap['xy']
            mass = snap['mass']
            if len(xy) > 0:
                ax.hexbin(xy[:, 0], xy[:, 1], C=mass, reduce_C_function=np.sum, gridsize=46, cmap='magma', mincnt=1, alpha=0.82)
            ax.axhline(self.flow_model.coast.y_coast, color='saddlebrown', lw=3)
            ax.fill_between(self.flow_model.domain['x'], self.flow_model.coast.y_coast - 25, self.flow_model.coast.y_coast, color='burlywood', alpha=0.95)
            for net, color in zip(self.flow_model.nets, ['tab:green', 'tab:orange', 'tab:red']):
                circle = plt.Circle(net.center, net.radius, edgecolor='black', facecolor=color, alpha=0.30, lw=1.6)
                ax.add_patch(circle)
            ax.set_title(f't = {t_s} s')
            ax.set_aspect('equal')
            ax.set_xlim(self.flow_model.domain['x'])
            ax.set_ylim(self.flow_model.domain['y'])
            ax.grid(True, alpha=0.15)
            ax.set_xlabel('x [m]')
            ax.set_ylabel('y [m]')
        axes[-1].axis('off')
        fig.suptitle(f"AquaGuard coastal pathogen – {case_result['case_name']} – 3 nets + coastline + biology v1.22", fontsize=14, y=1.01)
        out = self.output_dir / filename
        fig.savefig(out, dpi=170, bbox_inches='tight')
        plt.close(fig)
        self._log(f"  Ferdig lagret: {out}")
        return out

    def render_concentration_timeseries(self, case_result: dict, filename: str) -> Path:
        self._log(f"Renderer konsentrasjonstidsserie for '{case_result['case_name']}' -> {filename}")
        ts = case_result['time_series']
        t_min = ts['time_s'].to_numpy() / 60.0
        fig, ax = plt.subplots(figsize=(10.8, 5.8))
        for net, color in zip(self.flow_model.nets, ['tab:green', 'tab:orange', 'tab:red']):
            safe = net.name.lower().replace(' ', '_')
            ax.plot(t_min, ts[f'{safe}_conc_rel'], lw=2.0, color=color, label=f'{net.name} aktiv conc (S={net.solidity:.2f})')
            if self.species_infectivity_factor != 1.0:
                ax.plot(t_min, ts[f'{safe}_risk_conc_rel'], lw=1.2, ls='--', color=color, alpha=0.85, label=f'{net.name} risiko-vektet')
        ax.set_title(f"Relativ biologisk aktiv pathogen-konsentrasjon inne i nøtene – {case_result['case_name']} – kystcase")
        ax.set_xlabel('Tid [min]')
        ax.set_ylabel('Relativ aktiv konsentrasjon [masse / m²]')
        ax.grid(True, alpha=0.25)
        ax.legend()
        out = self.output_dir / filename
        fig.tight_layout()
        fig.savefig(out, dpi=180, bbox_inches='tight')
        plt.close(fig)
        self._log(f"  Ferdig lagret: {out}")
        return out


    def _standardize_summary_df(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        """Returner summary_df med standardiserte kolonnenavn og valider nødvendige felter."""
        if summary_df is None:
            raise ValueError("summary_df is None; cannot continue.")
        if not isinstance(summary_df, pd.DataFrame):
            summary_df = pd.DataFrame(summary_df)
        out = summary_df.copy()
        if 'case_name' not in out.columns and 'direction' in out.columns:
            out['case_name'] = out['direction']
        if 'direction' not in out.columns and 'case_name' in out.columns:
            out['direction'] = out['case_name']

        required_cols = [
            'case_name', 'direction', 'net', 'risk_status',
            'first_arrival_s', 'total_risk_exposure_mass_seconds'
        ]
        missing = [c for c in required_cols if c not in out.columns]
        if missing:
            raise KeyError(
                "summary_df mangler nødvendige kolonner for videre rapportering: "
                + ", ".join(missing)
                + f". Tilgjengelige kolonner: {list(out.columns)}"
            )
        return out


    def render_operational_risk_plot(self, case_result: dict, filename: str) -> Path:
        """Lag et operativt risikoplot per case med status, ankomsttid og eksponering."""
        self._log(f"Renderer operativt risikoplot for '{case_result['case_name']}' -> {filename}")
        summary = self._standardize_summary_df(case_result['summary'])
        if summary.empty:
            raise ValueError("case_result['summary'] is empty; cannot render risk plot.")

        status_order = {'GREEN': 0, 'YELLOW': 1, 'RED': 2}
        status_color = {'GREEN': '#2ca02c', 'YELLOW': '#ffbf00', 'RED': '#d62728'}
        nets = summary['net'].tolist()
        y = np.arange(len(nets))
        colors = [status_color.get(str(s).upper(), '#808080') for s in summary['risk_status']]

        fig, axes = plt.subplots(1, 3, figsize=(16.8, 5.8), constrained_layout=True)

        ax = axes[0]
        status_vals = [status_order.get(str(s).upper(), 0) for s in summary['risk_status']]
        ax.barh(y, status_vals, color=colors, edgecolor='black', alpha=0.85)
        ax.set_yticks(y)
        ax.set_yticklabels(nets)
        ax.set_xlim(0, 2.6)
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(['GREEN', 'YELLOW', 'RED'])
        ax.set_title('Operativ risikostatus')
        ax.grid(True, axis='x', alpha=0.2)
        for i, row in summary.iterrows():
            alarm_txt = 'ALARM' if bool(row.get('operational_alarm', False)) else 'OK'
            ax.text(min(status_vals[i] + 0.05, 2.45), i, f"{row['risk_status']} | {alarm_txt}", va='center', fontsize=9)

        ax = axes[1]
        arrival_min = []
        for v in summary['first_arrival_s']:
            if pd.isna(v):
                arrival_min.append(np.nan)
            else:
                arrival_min.append(float(v) / 60.0)
        arr_plot = [v if np.isfinite(v) else 0.0 for v in arrival_min]
        ax.barh(y, arr_plot, color=colors, edgecolor='black', alpha=0.85)
        ax.set_yticks(y)
        ax.set_yticklabels(nets)
        ax.set_title('Første ankomsttid')
        ax.set_xlabel('Tid [min]')
        ax.grid(True, axis='x', alpha=0.2)
        ax.axvline(self.red_arrival_threshold_s / 60.0, color='#d62728', ls='--', lw=1.5, label='Rød terskel')
        ax.axvline(self.yellow_arrival_threshold_s / 60.0, color='#ffbf00', ls='--', lw=1.5, label='Gul terskel')
        max_arr = max([v for v in arr_plot if np.isfinite(v)] + [1.0])
        for i, v in enumerate(arrival_min):
            label = 'Ingen ankomst' if not np.isfinite(v) else f'{v:.1f} min'
            ax.text(arr_plot[i] + 0.03 * max_arr, i, label, va='center', fontsize=9)
        ax.legend(loc='lower right')

        ax = axes[2]
        exposure = summary['total_risk_exposure_mass_seconds'].astype(float).to_numpy()
        ax.barh(y, exposure, color=colors, edgecolor='black', alpha=0.85)
        ax.set_yticks(y)
        ax.set_yticklabels(nets)
        ax.set_title('Total risiko-vektet eksponering')
        ax.set_xlabel('Relativ masse · s')
        ax.grid(True, axis='x', alpha=0.2)
        ax.axvline(self.red_exposure_threshold_mass_seconds, color='#d62728', ls='--', lw=1.5, label='Rød terskel')
        ax.axvline(self.yellow_exposure_threshold_mass_seconds, color='#ffbf00', ls='--', lw=1.5, label='Gul terskel')
        max_exp = max(list(exposure) + [1.0])
        for i, v in enumerate(exposure):
            ax.text(v + 0.02 * max_exp, i, f'{v:.2f}', va='center', fontsize=9)
        ax.legend(loc='lower right')

        fig.suptitle(f"Operativt risikobilde – {case_result['case_name']} – AquaGuard v1.22", fontsize=14)
        out = self.output_dir / filename
        fig.savefig(out, dpi=180, bbox_inches='tight')
        plt.close(fig)
        self._log(f"  Ferdig lagret: {out}")
        return out

    def render_risk_heatmap(self, summary_df: pd.DataFrame, filename: str) -> Path:
        """Lag en enkel heatmap som viser operativ risiko per case og nøt."""
        self._log(f"Renderer samlet risiko-heatmap -> {filename}")
        summary_df = self._standardize_summary_df(summary_df)
        if summary_df.empty:
            raise ValueError("summary_df is empty; cannot render risk heatmap.")

        status_order = {'GREEN': 0, 'YELLOW': 1, 'RED': 2}
        case_col = 'case_name'
        cases = list(dict.fromkeys(summary_df[case_col].tolist()))
        nets = list(dict.fromkeys(summary_df['net'].tolist()))
        mat = np.full((len(cases), len(nets)), np.nan)
        labels = [['' for _ in nets] for _ in cases]

        for i, case in enumerate(cases):
            for j, net in enumerate(nets):
                sub = summary_df[(summary_df[case_col] == case) & (summary_df['net'] == net)]
                if not sub.empty:
                    row = sub.iloc[0]
                    mat[i, j] = status_order.get(str(row['risk_status']).upper(), np.nan)
                    arr = row.get('first_arrival_s', np.nan)
                    arr_txt = 'na' if pd.isna(arr) else f"{float(arr)/60.0:.1f}m"
                    labels[i][j] = f"{row['risk_status']}\n{arr_txt}"

        fig, ax = plt.subplots(figsize=(1.8 * len(nets) + 2.0, 1.1 * len(cases) + 2.4))
        cmap = matplotlib.colors.ListedColormap(['#2ca02c', '#ffbf00', '#d62728'])
        bounds = [-0.5, 0.5, 1.5, 2.5]
        norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)
        im = ax.imshow(mat, cmap=cmap, norm=norm, aspect='auto')

        ax.set_xticks(np.arange(len(nets)))
        ax.set_xticklabels(nets)
        ax.set_yticks(np.arange(len(cases)))
        ax.set_yticklabels(cases)
        ax.set_title('Samlet operativ risiko per retning og nøt')
        ax.set_xlabel('Nøt')
        ax.set_ylabel('Strømretning')

        for i in range(len(cases)):
            for j in range(len(nets)):
                if np.isfinite(mat[i, j]):
                    ax.text(j, i, labels[i][j], ha='center', va='center', fontsize=9, color='black')

        cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2], fraction=0.05, pad=0.04)
        cbar.ax.set_yticklabels(['GREEN', 'YELLOW', 'RED'])

        out = self.output_dir / filename
        fig.tight_layout()
        fig.savefig(out, dpi=180, bbox_inches='tight')
        plt.close(fig)
        self._log(f"  Ferdig lagret: {out}")
        return out

    def _log_operational_case_table(self, summary_df: pd.DataFrame, case_name: str) -> None:
        """Skriv ut en kompakt operativ tabell i konsollen etter hvert case."""
        summary_df = self._standardize_summary_df(summary_df)
        case_col = 'case_name'
        sub = summary_df[summary_df[case_col] == case_name].copy()
        if sub.empty:
            self._log(f"Ingen summary-rader å vise for case '{case_name}'.")
            return

        self._log(f"Operativ risikotabell for case '{case_name}':")
        header = (
            f"{'Nøt':<8} {'Status':<8} {'Alarm':<7} {'Ankomst [min]':>14} "
            f"{'Peak risk conc':>16} {'Eksponering':>14}  Handling"
        )
        self._log(f"  {header}")
        self._log(f"  {'-' * len(header)}")

        for _, row in sub.iterrows():
            arrival_s = row.get('first_arrival_s', np.nan)
            arrival_txt = 'na' if pd.isna(arrival_s) else f"{float(arrival_s)/60.0:6.1f}"
            peak_txt = f"{float(row.get('peak_relative_risk_concentration', 0.0)):.4f}"
            exposure_txt = f"{float(row.get('total_risk_exposure_mass_seconds', 0.0)):.1f}"
            alarm_txt = 'YES' if bool(row.get('operational_alarm', False)) else 'NO'
            action = str(row.get('recommended_action', ''))
            self._log(
                f"  {str(row.get('net', '')):<8} {str(row.get('risk_status', '')):<8} {alarm_txt:<7} "
                f"{arrival_txt:>14} {peak_txt:>16} {exposure_txt:>14}  {action}"
            )

    def run_all(self) -> dict:
        self._run_start = time.perf_counter()
        self._log(f"Output-mappe: {self.output_dir}")
        self.flow_model._log_parameter_summary(self._log)
        self._log_parameter_summary()
        results = {}
        summary_frames = []
        output_files = []
        metadata = {
            'case': 'three_nets_coastline_pathogen_v1.22_risk_autocal',
            'coast_y_m': self.flow_model.coast.y_coast,
            'biology': {
                'enabled': self.biology_enabled,
                'base_inactivation_rate_1_s': self.base_inactivation_rate_1_s,
                'effective_inactivation_rate_1_s': self.effective_inactivation_rate_1_s(),
                'temperature_c': self.temperature_c,
                'reference_temperature_c': self.reference_temperature_c,
                'q10_inactivation': self.q10_inactivation,
                'uv_inactivation_factor': self.uv_inactivation_factor,
                'species_infectivity_factor': self.species_infectivity_factor,
                'minimum_infectivity': self.minimum_infectivity,
            },
            'risk_thresholds': {
                'arrival_alarm_threshold_s': self.arrival_alarm_threshold_s,
                'exposure_alarm_threshold_mass_seconds': self.exposure_alarm_threshold_mass_seconds,
                'yellow_arrival_threshold_s': self.yellow_arrival_threshold_s,
                'yellow_peak_risk_concentration': self.yellow_peak_risk_concentration,
                'yellow_exposure_threshold_mass_seconds': self.yellow_exposure_threshold_mass_seconds,
                'red_arrival_threshold_s': self.red_arrival_threshold_s,
                'red_peak_risk_concentration': self.red_peak_risk_concentration,
                'red_exposure_threshold_mass_seconds': self.red_exposure_threshold_mass_seconds,
                'no_arrival_means_green': self.no_arrival_means_green,
                'auto_calibrate_from_first_case': self.auto_calibrate_from_first_case,
                'baseline_case_name': self.baseline_case_name,
                'baseline_peak_reference': self.baseline_peak_reference,
                'baseline_exposure_reference': self.baseline_exposure_reference,
                'yellow_peak_factor': self.yellow_peak_factor,
                'red_peak_factor': self.red_peak_factor,
                'yellow_exposure_factor': self.yellow_exposure_factor,
                'red_exposure_factor': self.red_exposure_factor,
                'baseline_min_peak': self.baseline_min_peak,
                'baseline_min_exposure': self.baseline_min_exposure,
            },
            'nets': [
                {'name': n.name, 'center': n.center, 'diameter_m': 2*n.radius, 'depth_m': n.depth, 'soliditet': n.solidity, 'beta': n.beta}
                for n in self.flow_model.nets
            ],
        }
        case_list = list(RUN_USER_SETTINGS['cases'])
        self._log(f"Starter full analyse for {len(case_list)} strømretninger: {', '.join(case_list)}")

        for idx, case_name in enumerate(case_list, start=1):
            self._log(f"=== Case {idx}/{len(case_list)}: {case_name} ===")
            res = self.run_case(case_name)
            if self.auto_calibrate_from_first_case and (not self._risk_autocalibrated):
                should_calibrate = (case_name == self.baseline_case_name) or (idx == 1 and self.baseline_case_name not in case_list)
                if should_calibrate:
                    self._apply_auto_risk_calibration(res['summary'], baseline_case_name=case_name)
                    res['summary'] = self._reclassify_summary_df(res['summary'])
            results[case_name] = res
            summary_frames.append(res['summary'])
            if not res['summary'].empty:
                order = {'GREEN': 0, 'YELLOW': 1, 'RED': 2}
                worst_row = max(res['summary'].to_dict('records'), key=lambda r: order.get(str(r.get('risk_status', 'GREEN')).upper(), 0))
                self._log(
                    f"Case '{case_name}' høyeste operative risiko: {worst_row['risk_status']} i {worst_row['net']} | "
                    f"handling: {worst_row['recommended_action']}"
                )
            self._log_operational_case_table(res['summary'], case_name)

            output_files.append(str(self.render_snapshot_grid(res, f'aquaguard_coast_pathogen_{case_name}_7samples_v122b.png')))
            output_files.append(str(self.render_concentration_timeseries(res, f'aquaguard_coast_pathogen_{case_name}_concentration_v122b.png')))
            output_files.append(str(self.render_operational_risk_plot(res, f'aquaguard_coast_pathogen_{case_name}_risk_v122b.png')))
            ts_path = self.output_dir / f'aquaguard_coast_pathogen_{case_name}_timeseries_v122b.csv'
            res['time_series'].to_csv(ts_path, index=False)
            output_files.append(str(ts_path))
            self._log(f"Lagrer tidsserie CSV: {ts_path}")

        summary = pd.concat(summary_frames, ignore_index=True)
        summary_path = self.output_dir / 'aquaguard_coast_pathogen_summary_v122b.csv'
        summary.to_csv(summary_path, index=False)
        output_files.append(str(summary_path))
        self._log(f"Lagrer summary CSV: {summary_path}")
        risk_heatmap_path = self.render_risk_heatmap(summary, 'aquaguard_coast_pathogen_risk_heatmap_v122b.png')
        output_files.append(str(risk_heatmap_path))

        if self._risk_baseline_info:
            metadata['risk_baseline'] = self._risk_baseline_info
        metadata['outputs'] = output_files
        metadata_path = self.output_dir / 'aquaguard_coast_pathogen_metadata_v122b.json'
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        self._log(f"Lagrer metadata JSON: {metadata_path}")
        self._log("Analyse ferdig.")
        return {'results': results, 'summary': summary, 'summary_path': summary_path, 'metadata_path': metadata_path}

def print_user_settings() -> None:
    """Skriv ut de viktigste brukerinnstillingene samlet."""
    print('=== USER SETTINGS ===')
    print('FLOW_USER_SETTINGS =', FLOW_USER_SETTINGS)
    print('NET_USER_SETTINGS =', NET_USER_SETTINGS)
    print('COAST_USER_SETTINGS =', COAST_USER_SETTINGS)
    print('DOMAIN_USER_SETTINGS =', DOMAIN_USER_SETTINGS)
    print('pathogen_USER_SETTINGS =', pathogen_USER_SETTINGS)
    print('RISK_USER_SETTINGS =', RISK_USER_SETTINGS)
    print('RUN_USER_SETTINGS =', RUN_USER_SETTINGS)


def run_demo(verbose: bool | None = None) -> dict:
    """
    Kjør standarddemo med verdiene fra USER SETTINGS-seksjonen øverst i fila.

    Hvis ``verbose`` sendes inn eksplisitt, overstyrer den bare denne ene
    parameteren. Alle øvrige verdier hentes fra ``FLOW_USER_SETTINGS``,
    ``NET_USER_SETTINGS``, ``COAST_USER_SETTINGS``, ``DOMAIN_USER_SETTINGS``
    og ``pathogen_USER_SETTINGS``.
    """
    model = CoastalThreeNetFlowModel()
    pathogen_cfg = dict(PATHOGEN_USER_SETTINGS)
    pathogen_cfg.update(RISK_USER_SETTINGS)
    if verbose is not None:
        pathogen_cfg['verbose'] = bool(verbose)
    marcher = CoastalpathogenTimeMarcher(model, **pathogen_cfg)
    return marcher.run_all()


if __name__ == '__main__' and RUN_USER_SETTINGS['auto_run_when_main']:
    outputs = run_demo()
    print(outputs['summary'])
