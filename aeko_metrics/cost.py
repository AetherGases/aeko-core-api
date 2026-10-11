"""Compute USD cost from agent token usage and a per-model price table."""


def cost_usd(used_agents, prices: dict) -> float:
    """Return the total USD cost for all agent invocations, rounded to six decimal places."""
    total = 0.0
    for agent in used_agents:
        model = prices.get(agent.llm) or {}
        input_rate = float(model.get("input_per_million", 0) or 0)
        output_rate = float(model.get("output_per_million", 0) or 0)
        total += agent.input_tokens * input_rate / 1_000_000
        total += agent.output_tokens * output_rate / 1_000_000
    return round(total, 6)
