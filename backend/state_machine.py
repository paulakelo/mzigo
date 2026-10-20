"""Mzigo Delivery State Machine.

Enforces legal delivery state transitions:
created -> assigned -> picked_up -> in_transit -> (delivered | failed)
"""

from enum import StrEnum


class DeliveryStatus(StrEnum):
    CREATED = "created"
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"


# Permitted transition map
LEGAL_TRANSITIONS: dict[DeliveryStatus, set[DeliveryStatus]] = {
    DeliveryStatus.CREATED: {DeliveryStatus.ASSIGNED, DeliveryStatus.FAILED},
    DeliveryStatus.ASSIGNED: {DeliveryStatus.PICKED_UP, DeliveryStatus.FAILED},
    DeliveryStatus.PICKED_UP: {DeliveryStatus.IN_TRANSIT, DeliveryStatus.FAILED},
    DeliveryStatus.IN_TRANSIT: {DeliveryStatus.DELIVERED, DeliveryStatus.FAILED},
    DeliveryStatus.DELIVERED: set(),  # Terminal state
    DeliveryStatus.FAILED: set(),  # Terminal state
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal status transition is attempted."""

    def __init__(self, from_status: str, to_status: str):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Illegal state transition from '{from_status}' to '{to_status}'. "
            f"Allowed transitions from '{from_status}': "
            f"{[s.value for s in LEGAL_TRANSITIONS.get(DeliveryStatus(from_status), set())]}"
        )


def validate_transition(
    current_status: str | DeliveryStatus, target_status: str | DeliveryStatus
) -> bool:
    """Validate whether transitioning from current_status to target_status is legal.

    Raises:
        InvalidStateTransitionError: If transition is illegal.
    """
    current = DeliveryStatus(current_status)
    target = DeliveryStatus(target_status)

    allowed = LEGAL_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransitionError(current.value, target.value)
    return True
