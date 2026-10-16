import logging

from .common import cached, store


logger = logging.getLogger(__name__)
LABEL = "LifecycleElements"


def _as_dict(model):
    """Serialize an SDK model when creating a report row."""
    return model.model_dump(mode="python")


def _event_views(actions, triggers):
    """Build orchestration-event and consuming-trigger report rows."""
    events = {
        action["id"]: action
        for action in actions
        if action.get("type") == 3 and action.get("id") is not None
    }
    consumers_by_event = {}
    for trigger in triggers:
        event_id = trigger.get("orchestrationEventId")
        if trigger.get("type") == 2 and event_id in events:
            consumers_by_event.setdefault(event_id, []).append(trigger)

    event_rows = []
    for event_id, action in events.items():
        consumers = consumers_by_event.get(event_id, [])
        event_rows.append({
            **action,
            "lifecycleName": action.get("lifecycleName"),
            "triggerName": action.get("triggerName"),
            "consumeOrchestrationEvents": ", ".join(
                trigger.get("name", str(trigger["id"])) for trigger in consumers
            ),
        })

    consume_rows = []
    for event_id, event_triggers in consumers_by_event.items():
        event_name = events[event_id].get("name", str(event_id))
        for trigger in event_triggers:
            consume_rows.append({
                **trigger,
                "orchestrationEventId": event_name,
                "lifecycleName": trigger.get("lifecycleName"),
            })
    return event_rows, consume_rows


def _with_event_views(used):
    """Return a copy of cached results with optional event report sections."""
    result = dict(used)
    event_rows, consume_rows = _event_views(result["actions"], result["triggers"])
    result["orchestration_events"] = event_rows
    result["consume_orchestration_events"] = consume_rows
    return result


def search(client, include_orchestration_events=False):
    """Find used and unused lifecycle elements from SDK lifecycle models."""
    if result := cached(client, "lifecycle_elements"):
        used, unused = result
        return (_with_event_views(used), unused) if include_orchestration_events else result

    categories = ("lifecycles", "states", "triggers", "transitions")
    used = {key: [] for key in categories}
    unused = {key: [] for key in categories}
    action_rows = []

    for lifecycle in client.lifecycle.get_all_lifecycles():
        logger.info("Searching lifecycle %s (%s)", lifecycle.name, lifecycle.id)

        object_type_id = lifecycle.objectTypeId
        lifecycle_id = lifecycle.id
        details = client.lifecycle.get_states_and_transitions(object_type_id, lifecycle_id)
        states = details.states or []
        triggers = details.triggers or []
        transitions = details.transitions or []

        state_map = {state.id: state for state in states}
        trigger_map = {trigger.id: trigger for trigger in triggers}
        transition_map = {transition.id: transition for transition in transitions}
        actions = {
            transition_id: client.lifecycle.get_transition_actions(
                object_type_id, lifecycle_id, transition_id
            ) or []
            for transition_id in transition_map
        }

        # Keep SDK models intact while resolving lifecycle relationships.
        state_by_trigger = {
            trigger_id: state.id
            for state in states
            for trigger_id in (state.triggers or [])
        }
        source_by_transition = {
            transition_id: state_by_trigger.get(transition.triggerId)
            for transition_id, transition in transition_map.items()
        }

        self_transitions = {
            transition_id
            for transition_id, transition in transition_map.items()
            if source_by_transition[transition_id] is not None
            and transition.destinationStateId == source_by_transition[transition_id]
            and not actions[transition_id]
        }
        empty_triggers = {
            trigger_id
            for trigger_id, trigger in trigger_map.items()
            if not (trigger.transitions or [])
            or all(transition_id in self_transitions for transition_id in (trigger.transitions or []))
        }

        destinations = {transition.destinationStateId for transition in transitions}
        empty_states = {
            state_id
            for state_id, state in state_map.items()
            if (
                (not (state.triggers or []) or all(trigger_id in empty_triggers for trigger_id in (state.triggers or [])))
                and state.stateCategoryId != 3
            ) or (state_id not in destinations and state.stateCategoryId is not None)
        }

        (unused if len(empty_states) == len(states) else used)["lifecycles"].append(lifecycle)
        for name, mapping, ignored in (
            ("states", state_map, empty_states),
            ("triggers", trigger_map, empty_triggers),
            ("transitions", transition_map, self_transitions),
        ):
            used[name].extend(value for key, value in mapping.items() if key not in ignored)
            unused[name].extend(value for key, value in mapping.items() if key in ignored)

        for transition_id, transition_actions in actions.items():
            transition = transition_map[transition_id]
            trigger = trigger_map.get(transition.triggerId)
            for action in transition_actions:
                action_rows.append((action, lifecycle, trigger, transition))

    # Convert only at the report boundary. Downstream searches and workbook
    # generation retain their existing dictionary based result contract.
    for name in categories:
        used[name] = [_as_dict(model) for model in used[name]]
        unused[name] = [_as_dict(model) for model in unused[name]]
    used["actions"] = [
        {
            **_as_dict(action),
            "lifecycleId": lifecycle.id,
            "lifecycleName": lifecycle.name,
            "triggerId": trigger.id if trigger else None,
            "triggerName": trigger.name if trigger else None,
            "transitionId": transition.id,
            "transitionName": transition.name,
        }
        for action, lifecycle, trigger, transition in action_rows
    ]

    if include_orchestration_events:
        used = _with_event_views(used)
        unused["orchestration_events"] = []
        unused["consume_orchestration_events"] = []

    return store(client, "lifecycle_elements", (used, unused))
