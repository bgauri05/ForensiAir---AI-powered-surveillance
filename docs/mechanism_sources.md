# ForensiAIR Mechanism B Injection Specification & Fault Rationales

**Protocol Version:** PROTOCOL v2.0 (Frozen)  
**Eligibility Standard:** PROTOCOL v1.1 Section C (Frozen)  
**Scope:** Development Set Injections (Seeds 301–305, Dev Factories Only)  
**Targeted Tamper Types:** T1, T2, T3, T7  

---

## 1. Overview & Motivation for Mechanism B

Mechanism A (V1) primarily evaluated canonical, hard-edged tampering patterns (e.g. perfect flatlines, exact unscaled copy-paste replays, extreme permit-breaching outliers, and constant step offsets). In real-world continuous effluent monitoring systems (OCEMS), sophisticated industrial operators and physical instrument failure modes exhibit more subtle, evasive behaviors designed to defeat naive thresholding and simple repeat-length checks.

**Mechanism B** introduces physically motivated and evasion-aware variants across four core tampering categories:
- **T1-B (Median Freeze with Flicker):** Dithered baseline freeze avoiding zero-variance flags.
- **T2-B (Scaled & Spliced Waveform Replays):** Gain-scaled and multi-source spliced replay attacks.
- **T3-B (Near-Limit Hugging & Variance Compression):** Near-permit limit operating bands without technical breach.
- **T4-B / T5-B / T6-B:** Excluded from Mechanism B (focused on sensor-level evasive manipulation).
- **T7-B (Transient Exponential & Triangular Drifts):** Realistic relaxation and progressive bias drifts.

---

## 2. Variant Rationales & Fault Patterns

### 2.1 T1-B: Median Freeze with Flicker
- **Fault / Fraud Pattern:** In automated SCADA monitoring, operators attempting to hide process upsets without triggering flatline alarms inject artificial dither (bit-level noise) around the instrument's recent median. Additionally, faulty A/D converters or stuck sample-and-hold circuits often display baseline quantization flicker ($\pm 1$ resolution step).
- **Mathematical Model:**
  $$x'_t = \text{round\_to\_res}\left(\mu_{\text{prior}} + \eta_t\right)$$
  where $\mu_{\text{prior}} = \text{median}(x_{t-672 : t-1})$ (for Flow: median of strictly non-zero readings in prior 7 days).  
  With probability $p$, a dither step $\eta_t \in \{-\text{step}, +\text{step}\}$ is added; with probability $1 - p$, $\eta_t = 0$.
- **Severity Magnitudes:**
  - **Subtle:** Flicker probability $p = 0.15$ (frequent dither, looks like noisy baseline).
  - **Moderate:** Flicker probability $p = 0.05$ (sparse occasional dither).
  - **Obvious:** Flicker probability $p = 0.00$ (pure frozen median flatline).

---

### 2.2 T2-B-scaled: Scaled Historical Waveform Replay
- **Fault / Fraud Pattern:** Replay attacks where an adversary captures compliant telemetry from a prior week and applies a slight scaling factor $s$ to match ambient temperatures, seasonal volume, or throughput targets, thwarting exact-match fingerprint engines.
- **Mathematical Model:**
  $$x'_t = \text{round\_to\_res}\left(s \times x_{t - \text{lag}}\right)$$
  where $\text{lag} \in [1, 7]$ days ($\text{lag\_rows} \in [96, 672]$ slots), source window is verified eligible with no event overlap.
- **Severity Magnitudes:**
  - **Subtle:** Scale distortion $|s - 1| \in [0.05, 0.10]$ (drawn uniformly from $[0.90, 0.95] \cup [1.05, 1.10]$).
  - **Moderate:** Scale distortion $|s - 1| \le 0.05$ (drawn uniformly from $[0.95, 1.05]$ excluding $1.0$).
  - **Obvious:** Scale factor $s = 1.0$ (exact unscaled copy-paste replay).

---

### 2.3 T2-B-splice: Multi-Segment Spliced Replay with Noise
- **Fault / Fraud Pattern:** To evade historical sequence alignment over long windows (e.g., 24h to 7d), telemetry from two distinct historical epochs is spliced at the window midpoint, with additive Gaussian noise masking the transition seam. Both donor source segments are sampled from 1–7 days back ($[96, 672]$ rows).
- **Mathematical Model:**
  For duration $D$:
  $$x'_t = \text{round\_to\_res}\left(x_{t - \text{lag}_1} + \epsilon_t\right) \quad \text{for } 0 \le t < \lfloor D/2 \rfloor, \quad \text{lag}_1 \in [1, 7] \text{ days}$$
  $$x'_t = \text{round\_to\_res}\left(x_{t - \text{lag}_2} + \epsilon_t\right) \quad \text{for } \lfloor D/2 \rfloor \le t < D, \quad \text{lag}_2 \in [1, 7] \text{ days}$$
  where $\epsilon_t \sim \mathcal{N}\left(0, (\sigma_{\text{noise}} \cdot \text{std}_{\text{series}})^2\right)$. Both donor source segments are verified eligible with no event overlap.
- **Severity Magnitudes:**
  - **Subtle:** Additive noise standard deviation $\sigma_{\text{noise}} = 0.05 \times \text{std}_{\text{series}}$ (5% of series std).
  - **Moderate:** Additive noise standard deviation $\sigma_{\text{noise}} = 0.01 \times \text{std}_{\text{series}}$ (1% of series std).
  - **Obvious:** Additive noise standard deviation $\sigma_{\text{noise}} = 0.00$ (pure spliced segments, 0% noise).

---

### 2.4 T3-B-ar1: Synthetic AR(1) Near-Limit Hugging
- **Fault / Fraud Pattern:** Operators running continuous bypasses program the telemetry logger to output realistic-looking effluent readings positioned just underneath regulatory CTO consent limits (e.g., 85%–99% of limit), avoiding statutory violation notices while hiding extreme pollutant loads. An AR(1) process with $\phi = 0.90$ matches natural process inertia.
- **Mathematical Model:**
  Only applied to series with an audited statutory upper consent limit $L$ from `consent_limits.csv` (no synthetic defaults).
  $$\tilde{x}_t - c \cdot L = \phi \left(\tilde{x}_{t-1} - c \cdot L\right) + \epsilon_t, \quad \phi = 0.90, \quad \epsilon_t \sim \mathcal{N}\left(0, (0.01 \cdot L)^2\right)$$
  $$x'_t = \text{round\_to\_res}(\tilde{x}_t)$$
  with target fraction $c$ drawn uniformly from severity-specific bands.
- **Severity Magnitudes:**
  - **Subtle:** Operating fraction $c \in [0.85, 0.92]$ (85% to 92% of CTO limit).
  - **Moderate:** Operating fraction $c \in [0.90, 0.96]$ (90% to 96% of CTO limit).
  - **Obvious:** Operating fraction $c \in [0.96, 0.99]$ (96% to 99% of CTO limit).

---

### 2.5 T3-B-pull: Continuous Variance-Preserving Limit Pull
- **Fault / Fraud Pattern:** Hardware attenuator or software gain clamp where real sensor fluctuations are compressed and pulled toward a ceiling of $0.95 \times \text{limit}$. Real high-load spikes are compressed while preserving underlying diurnal shape.
- **Mathematical Model:**
  $$x'_t = \text{round\_to\_res}\left(x_t + \lambda \times \left(0.95 \cdot L - x_t\right)\right) = \text{round\_to\_res}\left((1 - \lambda) x_t + 0.95 \lambda L\right)$$
  where $\lambda \in [0, 1]$ represents compression strength and $L$ is the parsed CTO limit.
- **Severity Magnitudes:**
  - **Subtle:** Pull factor $\lambda = 0.30$ (30% pull toward ceiling, 70% original signal preserved).
  - **Moderate:** Pull factor $\lambda = 0.60$ (60% pull toward ceiling, 40% original signal preserved).
  - **Obvious:** Pull factor $\lambda = 0.90$ (90% pull toward ceiling, high compression).

---

### 2.6 T7-B-step: Transient Exponential Step Drift
- **Fault / Fraud Pattern:** Optical or electrochemical sensor membrane fouling (e.g., biofilm accumulation on dissolved oxygen or pH probes) causing an abrupt calibration jump followed by asymptotic recovery as automated wash cycles or cleaning cycles engage.
- **Mathematical Model:**
  $$x'_t = \text{round\_to\_res}\left(x_t \times \left(1 + \text{sign} \cdot s \cdot \exp\left(-\frac{t}{\tau}\right)\right)\right)$$
  where $t \in [0, D-1]$ is the row step from event start, $\tau = D / 3.0$ is the relaxation time constant, and $\text{sign} \in \{-1, +1\}$ is chosen with equal probability.
- **Severity Magnitudes:**
  - **Subtle:** Peak step amplitude $s = 0.15$ ($\pm 15\%$ initial jump).
  - **Moderate:** Peak step amplitude $s = 0.30$ ($\pm 30\%$ initial jump).
  - **Obvious:** Peak step amplitude $s = 0.50$ ($\pm 50\%$ initial jump).

---

### 2.7 T7-B-tri: Symmetric Triangular Calibration Bias Drift
- **Fault / Fraud Pattern:** Diurnal thermal drift, progressive reagent exhaustion during colorimetric titration cycles, or gradual sensor offset ramping up to a peak and returning to zero without abrupt discontinuities.
- **Mathematical Model:**
  $$x'_t = \text{round\_to\_res}\left(x_t \times \left(1 + \text{sign} \cdot s \cdot \text{tri}(t)\right)\right)$$
  where $\text{tri}(t)$ is a normalized symmetric triangular ramp peaking at $1.0$ at midpoint $t = (D-1)/2$:
  $$\text{tri}(t) = 1.0 - \frac{|2t - (D - 1)|}{D - 1}$$
  and $\text{sign} \in \{-1, +1\}$ is chosen with equal probability.
- **Severity Magnitudes:**
  - **Subtle:** Peak amplitude $s = 0.15$ ($\pm 15\%$ maximum deviation).
  - **Moderate:** Peak amplitude $s = 0.30$ ($\pm 30\%$ maximum deviation).
  - **Obvious:** Peak amplitude $s = 0.50$ ($\pm 50\%$ maximum deviation).

---

## 3. Comprehensive Magnitude & Parameter Table

| Tamper Type | Variant Identifier | Target Mechanism | Severity: Subtle | Severity: Moderate | Severity: Obvious |
|:---|:---|:---|:---:|:---:|:---:|
| **T1** | `T1-B-freeze` | Median freeze + dither | $p = 0.15$ | $p = 0.05$ | $p = 0.00$ |
| **T2** | `T2-B-scaled` | Historical replay + gain scale | $\|s - 1\| \in [0.05, 0.10]$ | $\|s - 1\| \le 0.05$ | $s = 1.00$ (exact) |
| **T2** | `T2-B-splice` | Two-segment splice + noise | $\sigma_{\text{noise}} = 5\%$ std | $\sigma_{\text{noise}} = 1\%$ std | $\sigma_{\text{noise}} = 0\%$ std |
| **T3** | `T3-B-ar1` | AR(1) limit hugging ($\phi=0.9$) | $c \in [0.85, 0.92]$ | $c \in [0.90, 0.96]$ | $c \in [0.96, 0.99]$ |
| **T3** | `T3-B-pull` | Variance compression toward limit | $\lambda = 0.30$ | $\lambda = 0.60$ | $\lambda = 0.90$ |
| **T7** | `T7-B-step` | Exponential step decay ($\tau=D/3$) | $s = 0.15$ | $s = 0.30$ | $s = 0.50$ |
| **T7** | `T7-B-tri` | Symmetric triangular bias ramp | $s = 0.15$ | $s = 0.30$ | $s = 0.50$ |

*Physical Boundary Guards:* All modified telemetry is rounded to the series' empirical resolution step, non-negative ($x' \ge 0$), and clamped within $0 \le \text{pH} \le 14$ for pH sensors.

---

## 4. No-Op Tracking & Event Disclosures

To prevent unperturbed or mathematically trivial injections from distorting detector benchmarking, every Mechanism B injection event records four row-level change indicators in `labels_b.csv`:
- `n_rows_changed`: Count of rows where `value != value_orig`.
- `changed_share`: Ratio $\frac{n_{\text{rows\_changed}}}{D}$ across event duration $D$.
- `max_abs_change`: Maximum absolute displacement $\max_t |x'_t - x_t|$.
- `no_op`: Boolean flag set to `True` whenever `changed_share < 0.50` ($>50\%$ of rows identical to original readings).

Events flagged with `no_op = True` represent near-identical process periods where the injection transformation did not substantially alter the telemetry (e.g. historical donor segments that naturally coincided with the injection window, or extreme resolution quantization). Under Protocol v2.0, `no_op` events are excluded from training positives and primary recall denominators, and tracked separately for full audit transparency.
