from a10y.app import AvailabilityUI
import pytest

@pytest.mark.asyncio
async def test_send_button():
    """Test clicking the send button."""
    
   
    config = {
        "default_starttime": "2024-01-01T00:00:00",
        "default_endtime": "2024-01-02T00:00:00",
        "default_mergegaps": "0.0",
        "default_merge_samplerate": False,
        "default_merge_quality": False,
        "default_merge_overlap": False,
        "default_quality_D": False,
        "default_quality_R": False,
        "default_quality_Q": False,
        "default_quality_M": False,
        "default_includerestricted": False,
        "default_file": "",
    }

    app = AvailabilityUI(nodes_urls=[], routing = "https://www.orfeus-eu.org/eidaws/routing/1/query?", **config)

    async with app.run_test() as pilot:

        button = app.query_one("#request-button")
        assert button is not None, "Button not found!"

        # Click the send button
        await pilot.click("#request-button")


        assert button.disabled is True, "Button should be disabled after click"

        await pilot.pause(2)  # Waits for 500ms before checking the button

        assert button.disabled is False, "Button should be re-enabled after request found"

