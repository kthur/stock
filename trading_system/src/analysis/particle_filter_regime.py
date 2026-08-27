"""
particle_filter_regime.py — Sequential Monte Carlo (SMC) Bayesian Particle Filter Engine

Filters continuous latent macroeconomic parameter drift (mu_t, sigma_t) and instantaneous
crisis probabilities using 500-1000 particles, eliminating discrete regime switching lag.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union

logger = logging.getLogger(__name__)


class BayesianSMCParticleFilter:
    """
    Sequential Monte Carlo (SMC) Continuous Parameter Particle Filter.
    """

    def __init__(
        self,
        n_particles: int = 500,
        drift_volatility: float = 0.05,
        jump_probability: float = 0.02
    ):
        self.n_particles = n_particles
        self.drift_vol = drift_volatility
        self.jump_prob = jump_probability
        
        # Particle states: [mu_i, sigma_i, is_crisis_i]
        self._particles_mu = np.random.normal(0.08, 0.04, n_particles)
        self._particles_sigma = np.random.uniform(0.10, 0.25, n_particles)
        self._weights = np.ones(n_particles) / float(n_particles)

    def filter_returns_stream(
        self,
        daily_returns: Union[List[float], np.ndarray]
    ) -> Dict[str, Any]:
        """
        Updates particle weights sequentially via Bayes rule given new return observations:
        w_t^(p) propto w_{t-1}^(p) * N(r_t | mu_t^(p), sigma_t^(p)^2)
        """
        rets = np.nan_to_num(np.asarray(daily_returns, dtype=np.float64).ravel(), nan=0.0)
        if len(rets) == 0:
            return {
                "filtered_expected_return": 0.08,
                "filtered_volatility": 0.15,
                "crisis_probability": 0.05,
                "effective_sample_size": float(self.n_particles)
            }

        mu_p = self._particles_mu.copy()
        sigma_p = self._particles_sigma.copy()
        w = self._weights.copy()

        for r_t in rets:
            # 1. State Transition: Brownian drift + stochastic jumps
            drift_shocks = np.random.normal(0.0, self.drift_vol, self.n_particles)
            mu_p += drift_shocks * 0.01
            sigma_p = np.clip(sigma_p + drift_shocks * 0.02, 0.04, 1.20)

            # Jump injection
            jumps = np.random.rand(self.n_particles) < self.jump_prob
            sigma_p[jumps] *= np.random.uniform(1.30, 2.0, size=np.sum(jumps))

            # 2. Measurement Likelihood: Gaussian PDF on daily return
            dt_sigma = sigma_p / np.sqrt(252.0)
            dt_mu = mu_p / 252.0
            
            # Log-likelihood to prevent underflow
            z_scores = (r_t - dt_mu) / np.maximum(dt_sigma, 1e-4)
            log_lik = -0.5 * (z_scores ** 2) - np.log(np.maximum(dt_sigma, 1e-4))
            
            # Update log-weights
            log_w = np.log(np.maximum(w, 1e-12)) + log_lik
            # Softmax normalization
            max_lw = np.max(log_w)
            w = np.exp(log_w - max_lw)
            w /= np.maximum(np.sum(w), 1e-12)

            # 3. Systematic Resampling if Effective Sample Size (ESS) drops below N/2
            ess = 1.0 / np.sum(w ** 2)
            if ess < (self.n_particles / 2.0):
                cum_w = np.cumsum(w)
                u = (np.arange(self.n_particles) + np.random.rand()) / self.n_particles
                idx = np.searchsorted(cum_w, u)
                idx = np.clip(idx, 0, self.n_particles - 1)
                
                mu_p = mu_p[idx]
                sigma_p = sigma_p[idx]
                w = np.ones(self.n_particles) / float(self.n_particles)

        # Store posterior
        self._particles_mu = mu_p
        self._particles_sigma = sigma_p
        self._weights = w

        # Posterior expectations
        post_mu = float(np.sum(w * mu_p))
        post_sigma = float(np.sum(w * sigma_p))
        # Crisis probability: proportion of particles with annualized vol > 25% or mu < -10%
        crisis_particles = (sigma_p > 0.25) | (mu_p < -0.05)
        crisis_prob = float(np.sum(w * crisis_particles))

        return {
            "filtered_expected_return": round(post_mu, 4),
            "filtered_volatility": round(post_sigma, 4),
            "crisis_probability": round(float(np.clip(crisis_prob, 0.0, 1.0)), 4),
            "effective_sample_size": round(float(1.0 / max(np.sum(w ** 2), 1e-8)), 1)
        }
