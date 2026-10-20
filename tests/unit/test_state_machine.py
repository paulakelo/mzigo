"""Unit tests for Mzigo delivery state machine."""

import pytest

from backend.state_machine import DeliveryStatus, InvalidStateTransitionError, validate_transition


def test_valid_forward_transitions():
    assert validate_transition(DeliveryStatus.CREATED, DeliveryStatus.ASSIGNED) is True
    assert validate_transition(DeliveryStatus.ASSIGNED, DeliveryStatus.PICKED_UP) is True
    assert validate_transition(DeliveryStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT) is True
    assert validate_transition(DeliveryStatus.IN_TRANSIT, DeliveryStatus.DELIVERED) is True


def test_valid_failure_transitions():
    assert validate_transition(DeliveryStatus.CREATED, DeliveryStatus.FAILED) is True
    assert validate_transition(DeliveryStatus.ASSIGNED, DeliveryStatus.FAILED) is True
    assert validate_transition(DeliveryStatus.PICKED_UP, DeliveryStatus.FAILED) is True
    assert validate_transition(DeliveryStatus.IN_TRANSIT, DeliveryStatus.FAILED) is True


def test_illegal_jump_transitions():
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(DeliveryStatus.CREATED, DeliveryStatus.DELIVERED)

    with pytest.raises(InvalidStateTransitionError):
        validate_transition(DeliveryStatus.ASSIGNED, DeliveryStatus.DELIVERED)


def test_illegal_backward_transitions():
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(DeliveryStatus.DELIVERED, DeliveryStatus.IN_TRANSIT)

    with pytest.raises(InvalidStateTransitionError):
        validate_transition(DeliveryStatus.FAILED, DeliveryStatus.ASSIGNED)
