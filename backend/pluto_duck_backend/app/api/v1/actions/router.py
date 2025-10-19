"""Actions catalog endpoints."""

from fastapi import APIRouter

from pluto_duck_backend.app.services.actions import get_action_catalog

router = APIRouter()


@router.get("", response_model=dict)
def list_actions() -> dict:
    catalog = get_action_catalog()
    actions = [
        {
            "subject": action.subject,
            "action": action.action,
            "description": action.description,
        }
        for action in catalog.list_actions()
    ]
    return {"actions": actions}

