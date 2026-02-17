from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from typing import TypedDict, Literal


class OrderState(TypedDict):
    item: str
    quantity: int
    approved: bool | None
    status: str


def validate_order(state: OrderState):
    return {**state, "status": "validated"}


def request_approval(state: OrderState):
    decision = interrupt(
        {
            "type": "order_approval",
            "item": state["item"],
            "quantity": state["quantity"],
            "message": "Do you want to place this order?",
        }
    )
    return {**state, "approved": decision == "approve"}


def finalize_order(state: OrderState):
    if state["approved"]:
        return {**state, "status": "order_confirmed"}
    return {**state, "status": "order_cancelled"}


graph = StateGraph(OrderState)
graph.add_node("validate", validate_order)
graph.add_node("approve", request_approval)
graph.add_node("finalize", finalize_order)

graph.set_entry_point("validate")
graph.add_edge("validate", "approve")
graph.add_edge("approve", "finalize")
graph.add_edge("finalize", END)

order_app = graph.compile()
