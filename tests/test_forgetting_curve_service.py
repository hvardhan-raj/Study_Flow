from services import SchedulerService
from services.forgetting_curve import ForgettingCurveModel, PersonalFeatures


def test_forgetting_curve_model_is_disabled_in_single_user_build(session) -> None:
    model = ForgettingCurveModel(session)

    assert model.train_if_needed() is None
    assert model.predict_interval(fsrs_interval=3, features=PersonalFeatures()) is None
    assert model.load() is None


def test_scheduler_no_longer_exposes_personalized_model(session) -> None:
    scheduler = SchedulerService(session)

    assert not hasattr(scheduler, "forgetting_curve_model")
