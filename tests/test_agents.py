import pytest
from datetime import datetime
from unittest.mock import MagicMock
from app.agents.running_coach import RunningCoachAgent

MODEL = "claude-sonnet-4-6"


@pytest.fixture
def mock_anthropic():
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text="Ran 5.02 km vs planned 4 km walk. Exceeded distance. ITB noted.")]
    client.messages.create.return_value = response
    return client


@pytest.fixture
def agent(mock_anthropic):
    return RunningCoachAgent(mock_anthropic)


@pytest.fixture
def sample_activity():
    return {
        "id": 12345678,
        "name": "Morning Run",
        "type": "Run",
        "sport_type": "Run",
        "description": "Easy loop around the park. Left ITB felt tight.",
        "workout_type": 0,
        "start_date": "2026-05-10",
        "start_date_local": datetime(2026, 5, 10, 7, 0, 0),
        "distance": 5020.0,
        "moving_time": 1860,
        "elapsed_time": 1920,
        "average_speed": 2.70,
        "max_speed": 4.10,
        "total_elevation_gain": 42.0,
        "elev_high": 185.0,
        "elev_low": 143.0,
        "average_heartrate": None,
        "max_heartrate": None,
        "average_cadence": 85.5,
        "average_watts": None,
        "average_temp": 18,
        "calories": 312.0,
        "suffer_score": 32,
        "perceived_exertion": None,
        "splits_metric": [
            {"split": 1, "distance": 1000.0, "moving_time": 372, "elapsed_time": 377,
             "average_speed": 2.69, "elevation_difference": 5.0, "average_heartrate": 148.0, "pace_zone": 2},
            {"split": 2, "distance": 1000.0, "moving_time": 368, "elapsed_time": 373,
             "average_speed": 2.72, "elevation_difference": -3.0, "average_heartrate": 150.0, "pace_zone": 2},
            {"split": 3, "distance": 1000.0, "moving_time": 370, "elapsed_time": 375,
             "average_speed": 2.70, "elevation_difference": 8.0, "average_heartrate": 152.0, "pace_zone": 2},
            {"split": 4, "distance": 1000.0, "moving_time": 375, "elapsed_time": 380,
             "average_speed": 2.67, "elevation_difference": -2.0, "average_heartrate": 151.0, "pace_zone": 2},
            {"split": 5, "distance": 20.0,   "moving_time": 7,   "elapsed_time": 8,
             "average_speed": 2.86, "elevation_difference": 0.0, "average_heartrate": 149.0, "pace_zone": 2},
        ],
    }


@pytest.fixture
def sample_planned():
    return {
        "row_index": 7,
        "day": "Sunday",
        "date": "05/10/2026",
        "session_type": "Walk",
        "planned": "4km walk",
        "athlete_comments": "Ran 5k outdoor. Legs felt heavy at the start but by the end, they felt fine",
    }


class TestAnalyzeAPICall:
    def test_calls_messages_create(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        mock_anthropic.messages.create.assert_called_once()

    def test_uses_correct_model(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        call_kwargs = mock_anthropic.messages.create.call_args.kwargs
        assert call_kwargs["model"] == MODEL

    def test_sets_max_tokens(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        call_kwargs = mock_anthropic.messages.create.call_args.kwargs
        assert "max_tokens" in call_kwargs
        assert call_kwargs["max_tokens"] > 0

    def test_includes_system_prompt(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        call_kwargs = mock_anthropic.messages.create.call_args.kwargs
        assert "system" in call_kwargs
        assert len(call_kwargs["system"]) > 0

    def test_sends_user_message(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        call_kwargs = mock_anthropic.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) >= 1
        assert messages[0]["role"] == "user"


class TestAnalyzePromptContent:
    def _get_user_message(self, mock_anthropic) -> str:
        return mock_anthropic.messages.create.call_args.kwargs["messages"][0]["content"]

    def _get_system_prompt(self, mock_anthropic) -> str:
        return mock_anthropic.messages.create.call_args.kwargs["system"]

    def test_system_prompt_instructs_factual_tone(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        system = self._get_system_prompt(mock_anthropic).lower()
        assert any(word in system for word in ["factual", "concise", "brief"])

    # --- Plan ---

    def test_prompt_includes_planned_session(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        assert "4km walk" in self._get_user_message(mock_anthropic)

    def test_prompt_includes_athlete_comments(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        assert sample_planned["athlete_comments"] in self._get_user_message(mock_anthropic)

    def test_prompt_omits_athlete_comments_when_empty(self, agent, mock_anthropic, sample_activity, sample_planned):
        sample_planned["athlete_comments"] = ""
        agent.analyze(sample_activity, sample_planned)

        assert "Legs felt heavy" not in self._get_user_message(mock_anthropic)

    # --- Activity description ---

    def test_prompt_includes_activity_description(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        assert "Left ITB felt tight" in self._get_user_message(mock_anthropic)

    def test_prompt_omits_description_when_none(self, agent, mock_anthropic, sample_activity, sample_planned):
        sample_activity["description"] = None
        agent.analyze(sample_activity, sample_planned)

        assert "Left ITB felt tight" not in self._get_user_message(mock_anthropic)

    # --- Distance, speed, pace ---

    def test_prompt_includes_actual_distance(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        assert "5.02" in self._get_user_message(mock_anthropic)

    def test_prompt_includes_moving_time(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        content = self._get_user_message(mock_anthropic)
        assert "1860" in content or "31:00" in content or "31" in content

    def test_prompt_includes_activity_type(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        assert "Run" in self._get_user_message(mock_anthropic)

    # --- Heart rate ---

    def test_prompt_includes_avg_heartrate_when_present(self, agent, mock_anthropic, sample_activity, sample_planned):
        sample_activity["average_heartrate"] = 152.0
        agent.analyze(sample_activity, sample_planned)

        assert "152" in self._get_user_message(mock_anthropic)

    def test_prompt_includes_max_heartrate_when_present(self, agent, mock_anthropic, sample_activity, sample_planned):
        sample_activity["max_heartrate"] = 178
        agent.analyze(sample_activity, sample_planned)

        assert "178" in self._get_user_message(mock_anthropic)

    def test_prompt_omits_heartrate_when_none(self, agent, mock_anthropic, sample_activity, sample_planned):
        sample_activity["average_heartrate"] = None
        sample_activity["max_heartrate"] = None
        agent.analyze(sample_activity, sample_planned)

        content = self._get_user_message(mock_anthropic)
        assert "avg HR" not in content.lower() or "none" not in content.lower()

    # --- Elevation ---

    def test_prompt_includes_elevation_gain(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        content = self._get_user_message(mock_anthropic)
        assert "42" in content

    def test_prompt_omits_elevation_when_none(self, agent, mock_anthropic, sample_activity, sample_planned):
        sample_activity["total_elevation_gain"] = None
        sample_activity["elev_high"] = None
        sample_activity["elev_low"] = None
        agent.analyze(sample_activity, sample_planned)

        assert "elev_high" not in self._get_user_message(mock_anthropic)

    # --- Cadence, calories, effort ---

    def test_prompt_includes_cadence_when_present(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        assert "85" in self._get_user_message(mock_anthropic)

    def test_prompt_includes_calories(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        assert "312" in self._get_user_message(mock_anthropic)

    def test_prompt_includes_suffer_score(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        assert "32" in self._get_user_message(mock_anthropic)

    def test_prompt_includes_perceived_exertion_when_present(self, agent, mock_anthropic, sample_activity, sample_planned):
        sample_activity["perceived_exertion"] = 6
        agent.analyze(sample_activity, sample_planned)

        assert "6" in self._get_user_message(mock_anthropic)

    def test_prompt_includes_temperature(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        assert "18" in self._get_user_message(mock_anthropic)

    # --- Splits ---

    def test_prompt_includes_splits(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        content = self._get_user_message(mock_anthropic)
        assert "Split 1" in content or "split 1" in content.lower()

    def test_prompt_includes_all_splits(self, agent, mock_anthropic, sample_activity, sample_planned):
        agent.analyze(sample_activity, sample_planned)

        content = self._get_user_message(mock_anthropic)
        for i in range(1, 6):
            assert str(i) in content

    def test_prompt_omits_splits_when_none(self, agent, mock_anthropic, sample_activity, sample_planned):
        sample_activity["splits_metric"] = None
        agent.analyze(sample_activity, sample_planned)

        content = self._get_user_message(mock_anthropic)
        assert "Split 1" not in content


class TestAnalyzeReturnValue:
    def test_returns_response_text(self, agent, mock_anthropic, sample_activity, sample_planned):
        result = agent.analyze(sample_activity, sample_planned)

        assert result == "Ran 5.02 km vs planned 4 km walk. Exceeded distance. ITB noted."

    def test_returns_string(self, agent, mock_anthropic, sample_activity, sample_planned):
        result = agent.analyze(sample_activity, sample_planned)

        assert isinstance(result, str)
