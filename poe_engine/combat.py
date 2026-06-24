"""Combat resolution: hit chance, crit, mitigation and damage application.

The model is deliberately compact but mirrors the ARPG pipeline:

1. **Hit** -- accuracy is checked against evasion.
2. **Crit** -- a successful crit multiplies the whole hit.
3. **Mitigate** -- physical damage is reduced by armour; each elemental and
   chaos component is reduced by the matching resistance.
4. **Apply** -- damage is taken off energy shield first, then life.
"""

from dataclasses import dataclass, field

from .config import ROUND_DECIMALS
from .rng import chance_roll


@dataclass
class HitResult:
    hit: bool = False
    crit: bool = False
    total: float = 0.0
    breakdown: dict = field(default_factory=dict)

    def summary(self) -> str:
        if not self.hit:
            return "miss"
        tag = "CRIT " if self.crit else ""
        return f"{tag}{self.total} dmg"


def hit_chance(accuracy, evasion) -> float:
    """Return hit probability (0-100). High evasion lowers it."""
    accuracy = max(0.0, accuracy)
    evasion = max(0.0, evasion)
    if accuracy == 0:
        return 100.0
    raw = accuracy / (accuracy + (evasion / 4) ** 0.8) if (accuracy + evasion) else 1.0
    return max(5.0, min(95.0, raw * 100))


def _armour_mitigation(armour, raw_physical) -> float:
    """Fraction of physical damage prevented by *armour* (0-0.9)."""
    if raw_physical <= 0 or armour <= 0:
        return 0.0
    return min(0.9, armour / (armour + 10 * raw_physical))


def _damage_components(attacker):
    s = attacker.stats
    return {
        "physical": max(0.0, s.physicalDamage.totalStat),
        "fire": max(0.0, s.fireDamage.totalStat),
        "cold": max(0.0, s.coldDamage.totalStat),
        "lightning": max(0.0, s.lightningDamage.totalStat),
        "chaos": max(0.0, s.chaosDamage.totalStat),
    }


def _resistances(defender):
    s = defender.stats
    return {
        "fire": s.fireResistance.totalStat,
        "cold": s.coldResistance.totalStat,
        "lightning": s.lightningResistance.totalStat,
        "chaos": s.chaosResistance.totalStat,
    }


def attack(attacker, defender) -> HitResult:
    """Resolve a single attack from *attacker* against *defender*."""
    result = HitResult()

    chance = hit_chance(attacker.stats.accuracy.totalStat,
                        defender.stats.evasion.totalStat)
    if not chance_roll(chance):
        return result  # miss
    result.hit = True

    components = _damage_components(attacker)
    crit = attacker.stats.criticalStrikeChance.roll()
    result.crit = crit

    resistances = _resistances(defender)
    armour = defender.stats.armour.totalStat
    mitigation = _armour_mitigation(armour, components["physical"])

    total = 0.0
    for kind, raw in components.items():
        if raw <= 0:
            continue
        if crit:
            raw = attacker.stats.criticalStrikeDamage.calculateDamage(raw)
        if kind == "physical":
            dealt = raw * (1 - mitigation)
        else:
            dealt = raw * (1 - resistances.get(kind, 0) / 100)
        dealt = max(0.0, round(dealt, ROUND_DECIMALS))
        if dealt:
            result.breakdown[kind] = dealt
            total += dealt

    result.total = round(total, ROUND_DECIMALS)
    _apply_damage(defender, result.total)
    return result


def _apply_damage(defender, amount):
    es = defender.stats.energyShield
    if es.currentStat:
        absorbed = min(es.currentStat, amount)
        es.drain(absorbed)
        amount -= absorbed
    if amount > 0:
        defender.stats.life.drain(amount)
    defender.alive = defender.stats.life.currentStat > 0


def simulate_fight(attacker, defender, max_rounds=100, verbose=False):
    """Trade blows until someone dies or *max_rounds* is reached.

    Returns the winner (or ``None`` on a draw/timeout).
    """
    attacker.restore()
    defender.restore()
    order = [attacker, defender]

    for round_no in range(1, max_rounds + 1):
        for source, target in (order, order[::-1]):
            result = attack(source, target)
            if verbose:
                print(f"R{round_no}: {source.name} -> {target.name}: "
                      f"{result.summary()} "
                      f"(target life {target.stats.life.currentStat})")
            if not target.alive:
                return source
        for fighter in order:
            fighter.regenerate()
    return None
