from pathlib import Path
import numpy as np
from PIL import Image
from scipy.signal import convolve2d

COVER = Path(r"data\raw\BOSSBase_1.01\cover\5162.pgm")
WET_COST = 1e10
P = -1.0

# Daubechies 8 — dokładnie współczynniki z referencyjnego WOW.m
hpdf = np.array([
    -0.0544158422, 0.3128715909, -0.6756307363, 0.5853546837,
     0.0158291053, -0.2840155430, -0.0004724846, 0.1287474266,
     0.0173693010, -0.0440882539, -0.0139810279, 0.0087460940,
     0.0048703530, -0.0003917404, -0.0006754494, -0.0001174768
], dtype=np.float64)

lpdf = ((-1.0) ** np.arange(len(hpdf))) * hpdf[::-1]

F = [
    np.outer(lpdf, hpdf),
    np.outer(hpdf, lpdf),
    np.outer(hpdf, hpdf),
]

cover = np.asarray(Image.open(COVER), dtype=np.float64)

# MATLAB: padSize = 16; padarray(...,'symmetric')
pad_size = max(max(f.shape) for f in F)
cover_padded = np.pad(
    cover,
    ((pad_size, pad_size), (pad_size, pad_size)),
    mode="symmetric"
)

xis = []

for filt in F:
    # MATLAB conv2(...,'same')
    residual = convolve2d(
        cover_padded, filt, mode="same", boundary="fill", fillvalue=0
    )

    # MATLAB conv2(abs(R), rot90(abs(F),2),'same')
    suitability = convolve2d(
        np.abs(residual),
        np.rot90(np.abs(filt), 2),
        mode="same",
        boundary="fill",
        fillvalue=0
    )

    # WOW.m: dla parzystego filtra circshift o [1,1]
    suitability = np.roll(suitability, 1, axis=0)
    suitability = np.roll(suitability, 1, axis=1)

    # usunięcie paddingu
    suitability = suitability[
        pad_size:pad_size + cover.shape[0],
        pad_size:pad_size + cover.shape[1]
    ]

    xis.append(suitability)

with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
    rho = (
        xis[0] ** P +
        xis[1] ** P +
        xis[2] ** P
    ) ** (-1.0 / P)

# Zachowujemy informację przed progowaniem
nonfinite_before = ~np.isfinite(rho)
above_wet_before = rho > WET_COST

# Dokładnie logika WOW.m
rho[rho > WET_COST] = WET_COST
rho[np.isnan(rho)] = WET_COST

zero_mask = cover == 0
wet_mask = rho >= WET_COST

print("=== WOW diagnostic: BOSSBase 5162 ===")
print("Shape:", cover.shape)
print("Cover min/max:", int(cover.min()), int(cover.max()))
print("Zero pixels:", int(zero_mask.sum()))
print("Zero pixels [%]:", float(zero_mask.mean() * 100.0))
print()
print("Non-finite rho before threshold:", int(nonfinite_before.sum()))
print("rho > wetCost before threshold:", int(above_wet_before.sum()))
print("rho >= wetCost after threshold:", int(wet_mask.sum()))
print("rho >= wetCost [%]:", float(wet_mask.mean() * 100.0))
print()
print("Zero pixels with rho >= wetCost:", int((zero_mask & wet_mask).sum()))
print(
    "Fraction of zero pixels at wetCost [%]:",
    float((zero_mask & wet_mask).sum() / zero_mask.sum() * 100.0)
)
print()
print("Finite rho min:", float(np.nanmin(rho)))
print("Finite rho median:", float(np.nanmedian(rho)))
print("Finite rho max:", float(np.nanmax(rho)))

# ============================================================
# DIAGNOSTYKA LAMBDA — logika C++ mi_embedder.cpp
# ============================================================

def cost2probability_cpp(cost_m1, cost_0, cost_p1, lam):
    costs = np.stack([cost_m1, cost_0, cost_p1], axis=0).astype(np.float32)
    min_cost = np.min(costs, axis=0)

    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        e = np.exp(
            (-np.float32(lam) * (costs - min_cost)).astype(np.float32)
        ).astype(np.float32)
        div = np.sum(e, axis=0, dtype=np.float32)
        Pprob = e / div

    return Pprob


def average_payload_cpp(cost_m1, cost_0, cost_p1, lam):
    Pprob = cost2probability_cpp(cost_m1, cost_0, cost_p1, lam)

    H = np.zeros(Pprob.shape[1:], dtype=np.float64)

    for k in range(3):
        pk = Pprob[k].astype(np.float64)
        mask = pk > np.finfo(np.float64).tiny
        H[mask] -= pk[mask] * np.log(pk[mask])

    return float(H.sum() / np.log(2.0))


# Koszty dokładnie w kolejności C++: -1, 0, +1
cost_m1 = rho.astype(np.float32).copy()
cost_0  = np.zeros_like(cost_m1, dtype=np.float32)
cost_p1 = rho.astype(np.float32).copy()

cost_m1[cover == 0] = np.float32(WET_COST)
cost_p1[cover == 255] = np.float32(WET_COST)

rel_payload = 0.2

lambda1 = np.float32(0.0)
alpha1 = np.float32(1.0)

# mi_emb_calculate_lambda_from_payload(..., lambda_init=1, ...)
lambda_init = np.float32(1.0)
lambda3 = np.float32(0.5) * lambda_init
alpha3 = np.float32(10.0)

j = 0
iterations = 0

while alpha3 > rel_payload:
    lambda3 = np.float32(lambda3 * 2.0)
    alpha3 = np.float32(
        average_payload_cpp(cost_m1, cost_0, cost_p1, lambda3)
        / cover.size
    )
    j += 1
    iterations += 1
    if j > 100:
        break

lambda2 = lambda_init
alpha2 = alpha3

while float(alpha1 - alpha3) > rel_payload * 1e-2:
    lambda2 = np.float32(lambda1 + (lambda3 - lambda1) / 2.0)

    alpha2 = np.float32(
        average_payload_cpp(cost_m1, cost_0, cost_p1, lambda2)
        / cover.size
    )

    if alpha2 < rel_payload:
        lambda3 = lambda2
        alpha3 = alpha2
    else:
        lambda1 = lambda2
        alpha1 = alpha2

    iterations += 1

    if iterations > 100:
        break

lam = float(lambda2)

print()
print("=== C++ lambda diagnostic ===")
print("lambda:", lam)
print("alpha_out:", float(alpha2))
print("iterations:", iterations)

# Prawdopodobieństwa dla problematycznego przypadku:
# cover=0 oraz rho=wetCost => [-1,0,+1] = [1e10,0,1e10]
single_m1 = np.array([[WET_COST]], dtype=np.float32)
single_0  = np.array([[0.0]], dtype=np.float32)
single_p1 = np.array([[WET_COST]], dtype=np.float32)

p_wet = cost2probability_cpp(single_m1, single_0, single_p1, np.float32(lam))

p_minus = float(p_wet[0, 0, 0])
p_zero  = float(p_wet[1, 0, 0])
p_plus  = float(p_wet[2, 0, 0])

n_zero_wet = int((zero_mask & wet_mask).sum())

print()
print("For costs [1e10, 0, 1e10]:")
print("P(-1):", p_minus)
print("P(0) :", p_zero)
print("P(+1):", p_plus)
print()
print("Zero+wet pixels:", n_zero_wet)
print("Expected -1 selections:", n_zero_wet * p_minus)
print("Expected +1 selections:", n_zero_wet * p_plus)

# ============================================================
# POROWNANIE RZECZYWISTYCH ZMIAN Z MAPA wetCost
# ============================================================

STEGO = Path(r"data\stego\WOW\0.2\5162.pgm")
stego = np.asarray(Image.open(STEGO), dtype=np.int32)
cover_int = cover.astype(np.int32)

zero_wet = (cover_int == 0) & wet_mask
zero_nonwet = (cover_int == 0) & (~wet_mask)

print()
print("=== Actual changes split by wetCost ===")

print("ZERO + WET:")
print("pixels:", int(zero_wet.sum()))
print("0 -> 255:", int(np.sum(zero_wet & (stego == 255))))
print("0 -> 1  :", int(np.sum(zero_wet & (stego == 1))))
print("0 -> 0  :", int(np.sum(zero_wet & (stego == 0))))

print()
print("ZERO + NON-WET:")
print("pixels:", int(zero_nonwet.sum()))
print("0 -> 255:", int(np.sum(zero_nonwet & (stego == 255))))
print("0 -> 1  :", int(np.sum(zero_nonwet & (stego == 1))))
print("0 -> 0  :", int(np.sum(zero_nonwet & (stego == 0))))
