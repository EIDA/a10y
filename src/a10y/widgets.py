from textual.widgets import Static, Input, Button, Label, Select, Checkbox, SelectionList, LoadingIndicator
from textual.containers import Container, Horizontal, ScrollableContainer
from textual_autocomplete import AutoComplete, Dropdown
from textual.app import ComposeResult
from datetime import datetime
import os
from textual.suggester import Suggester
from textual import events
from rich.text import Text
from rich.cells import get_character_cell_size
from a10y import __version__

class Explanations(Static):
    """Explanations box with common key functions"""

    def compose(self) -> ComposeResult:
        yield Static("[b]Useful Keys[/b]", id="explanations-title")
        yield Static(
            """[gold3]ctrl+c[/gold3]: close app  [gold3]tab/shif+tab[/gold3]: cycle through options  [gold3]ctrl+s[/gold3]: send request  [gold3]esc[/gold3]: cancel request
            [gold3]up/down/pgUp/pgDown[/gold3]: scroll up/down if in scrollable window""",
            id="explanations-keys"
        )
        yield Static(f"[b]Version:[/b] {__version__}", classes="version")  # Styled version




class Requests(Static):
    def __init__(self, nodes_urls, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nodes_urls = nodes_urls  # Store nodes for later use
        self.config = config  # Store configuration for later use

    def compose(self) -> ComposeResult:
        yield Static("[b]Requests Control[/b]", id="request-title")
        yield Container(
            Checkbox("Deselect all ", False, id="all-nodes"),
            SelectionList(*self.nodes_urls, id="nodes"),
            id="nodes-container"

        )

        yield Horizontal(
            Label("Network:", classes="request-label"),
            AutoComplete(
                Input(classes="short-input", id="network"),
                Dropdown(items=[], id="networks")
            ),
            Label("Station:", classes="request-label"),
            AutoComplete(
                Input(classes="short-input", id="station"),
                Dropdown(items=[], id="stations")
            ),
            Label("Location:", classes="request-label"),
            AutoComplete(
                Input(classes="short-input", id="location"),
                Dropdown(items=[], id="locations")
            ),
            Label("Channel:", classes="request-label"),
            AutoComplete(
                Input(classes="short-input", id="channel"),
                Dropdown(items=[], id="channels")
            ),
            
            id="nslc"
        )
        
        
        yield Horizontal(
            Label("Start Time:", classes="request-label"),
            Input(classes="date-input", id="start", value=self.config["default_starttime"]),
            Label("End Time:", classes="request-label"),
            Input(classes="date-input", id="end", value=self.config["default_endtime"]),
            Select([
                ("last 24 hours", 1),
                ("last 2 days", 2),
                ("last 7 days", 3),
                ("this month", 4),
                ("last 2 months", 5),
                ("last 6 months", 6),
                ("this year", 7)
                ], prompt="Common time frames", id="times"),
            id="timeframe"
        )
        yield Horizontal(
            Label("Mergegaps:", classes="request-label"),
            Input(value=self.config["default_mergegaps"], type="number", id="mergegaps"),
            Label("Merge Options:", classes="request-label"),
            Checkbox("Samplerate", self.config["default_merge_samplerate"], id="samplerate"),
            Checkbox("Quality", self.config["default_merge_quality"], id="qual"),
            Checkbox("Overlap", self.config["default_merge_overlap"], id="overlap"),
            Label("Quality:", classes="request-label"),
            Checkbox("D", self.config["default_quality_D"], id="qd"),
            Checkbox("R", self.config["default_quality_R"], id="qr"),
            Checkbox("Q", self.config["default_quality_Q"], id="qq"),
            Checkbox("M", self.config["default_quality_M"], id="qm"),
            id="options"
        )
        yield Button("Reload Nodes\n(Restart the app)", variant="primary", id="reload-nodes", disabled=False)
        yield Horizontal(
            Checkbox("Include Restricted", self.config["default_includerestricted"], id="restricted"),
            Button("Send", variant="primary", id="request-button",disabled=False),
            Input(placeholder="Enter POST file path", value=self.config["default_file"], suggester=FileSuggester(), id="post-file"),
            Button("File", variant="primary", id="file-button"),
            id="send-request"
        )
        


class Status(Static):
    """Status line to show user what request is currently issued"""

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(Static(f'Welcome to Availability UI application version 1.0! 🙂\nCurrent session started at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', id="status-line"), id="status-container")


class Results(Static):
    """Show results widget"""

    def compose(self) -> ComposeResult:
        yield Static("[b]Results[/b]")
        yield LoadingIndicator(classes="hide", id="loading")
        yield Static(id="error-results", classes="hide")

class FileSuggester(Suggester):
    """A suggester for the POST file input"""

    def __init__(self) -> None:
        super().__init__(use_cache=True, case_sensitive=True)

    async def get_suggestion(self, value: str):
        """Suggestions are the matching files and folders of the directory the user has typed"""
        if value.startswith('/'):
            to_list = os.path.split(value)[0]
        else:
            to_list = os.path.join('./', os.path.split(value)[0])
        try:
            for suggestion in os.listdir(to_list):
                if suggestion.startswith(os.path.split(value)[1]):
                    return value + suggestion[len(os.path.split(value)[1]):]
        except:
            return None
        return None


class CursoredText(Input):
    """Widget that shows a Static text with a cursor that can be moved within text content"""

    DEFAULT_CSS = """
    CursoredText {
        background: $background;
        padding: 0 0;
        border: none;
        height: 1;
    }
    CursoredText:focus {
        border: none;
    }
    CursoredText>.input--cursor {
        background: $surface;
        color: $text;
        text-style: reverse;
    }
    """

    enriched = ""
    info = []

    def __init__(self, value=None, info=[], name=None, id=None, classes=None, disabled=False):
        super().__init__(value=Text.from_markup(value).plain, name=name, id=id, classes=classes, disabled=disabled)
        self.enriched = value
        self.info = info

    @property
    def _value(self) -> Text:
        """Value rendered as rich renderable"""
        return Text.from_markup(self.enriched)

    @property
    def _cursor_at_end(self) -> bool:
        """Flag to indicate if the cursor is at the end"""
        return self.cursor_position >= len(self.value) - 1

    def update_info_bar(self) -> None:
        """Update info bar when cursor moves"""
        if self.info[self.cursor_position][1]:
            if self.value[self.cursor_position] == ' ':
                #self.parent.parent.parent.parent.parent.query_one("#info-bar").update(f"Gap          Timestamp: {self.info[self.cursor_position][1]}     Gap start: {self.info[self.cursor_position][2]}     Gap end: {self.info[self.cursor_position][3]} ")
                self.parent.parent.parent.parent.parent.query_one("#info-bar").update(f"Gap          Timestamp: {self.info[self.cursor_position][1]} ")
            elif self.info[self.cursor_position][0].isdigit():
                self.parent.parent.parent.parent.parent.query_one("#info-bar").update(f"Gaps: {self.info[self.cursor_position][0]}      Timestamp: {self.info[self.cursor_position][1]}    Gaps start: {self.info[self.cursor_position][2]}    Gaps end: {self.info[self.cursor_position][3]} ")
            else:
                self.parent.parent.parent.parent.parent.query_one("#info-bar").update(f"Quality: {self.info[self.cursor_position][0]}   Timestamp: {self.info[self.cursor_position][1]}   Trace start: {self.info[self.cursor_position][2]}   Trace end: {self.info[self.cursor_position][3]} ")
        else:
            self.parent.parent.parent.parent.parent.query_one("#info-bar").update("")

    async def _on_key(self, event: events.Key) -> None:
        if event.is_printable:
            # capture nslc
            if event.character == 'c':
                nslc = self.id.split('_')[1:]
                self.parent.parent.parent.parent.parent.parent.query_one("#network").value = str(nslc[0])
                self.parent.parent.parent.parent.parent.parent.query_one("#station").value = str(nslc[1])
                self.parent.parent.parent.parent.parent.parent.query_one("#location").value = str(nslc[2])
                self.parent.parent.parent.parent.parent.parent.query_one("#channel").value = str(nslc[3])
            # capture timestamp as start time
            elif event.character == 's':
                self.parent.parent.parent.parent.parent.parent.query_one("#start").value = self.info[self.cursor_position][1]
            # capture timestamp as end time
            elif event.character == 'e':
                self.parent.parent.parent.parent.parent.parent.query_one("#end").value = self.info[self.cursor_position][1]
            # capture time span as start and end time
            elif event.character == 'z':
                self.parent.parent.parent.parent.parent.parent.query_one("#start").value = self.info[self.cursor_position][4].strftime("%Y-%m-%dT%H:%M:%S")
                self.parent.parent.parent.parent.parent.parent.query_one("#end").value = self.info[self.cursor_position][5].strftime("%Y-%m-%dT%H:%M:%S")
            # toggle results view
            elif event.character == 't':
                # self.parent.parent.parent.parent = ContentSwitcher
                self.parent.parent.parent.parent.current = "plain-container"
                if self.parent.parent.parent.parent.parent.parent.parent.focused in self.parent.parent.query(CursoredText):
                    active_nslc = self.parent.parent.parent.parent.parent.parent.parent.focused.id.split('_')[1:]
                    text = self.parent.parent.parent.parent.parent.parent.parent.parent.req_text.splitlines()
                    new_text = '\n'.join(text[:6])
                    for row in text[5:]:
                        parts = row.split('|')
                        if parts:
                            if all([p == an for (p, an) in zip(parts, active_nslc)]):
                                new_text += '\n' + row
                    self.parent.parent.parent.parent.query_one("#plain").update(new_text)
            # toggle help
            elif event.character == '?':
                self.parent.parent.parent.parent.parent.parent.parent.parent.action_toggle_help()
            # move to next trace
            elif event.character == 'n':
                temp1 = self.value.find(' ', self.cursor_position)
                temp2 = self.value.find('╌', self.cursor_position)
                temp3 = self.value.find('┄', self.cursor_position)
                temp4 = self.value.find('┗', self.cursor_position + 1)
                temp5 = self.value.find('┛', self.cursor_position)
                if max(temp1, temp2, temp3, temp4, temp5) != -1:
                    temp = min([n for n in (temp1, temp2, temp3, temp4, temp5) if n >= 0])
                    temp1 = self.value.find('━', temp)
                    temp2 = self.value.find('┗', temp + 1)
                    temp3 = self.value.find('┛', temp + 1)
                    if max(temp1, temp2, temp3) != -1:
                        self.cursor_position = min([n for n in (temp1, temp2, temp3) if n >= 0])
                    else:
                        self.parent.parent.parent.parent.parent.parent.parent.parent.next_line()
                else:
                    self.parent.parent.parent.parent.parent.parent.parent.parent.next_line()
                self.update_info_bar()
            # move to previous trace
            elif event.character == 'p':
                temp1 = self.value.rfind(' ', 0, self.cursor_position + 1)
                temp2 = self.value.rfind('╌', 0, self.cursor_position + 1)
                temp3 = self.value.rfind('┄', 0, self.cursor_position + 1)
                temp4 = self.value.rfind('┗', 0, self.cursor_position + 1)
                temp5 = self.value.rfind('┛', 0, self.cursor_position + 1)
                temp = max(temp1, temp2, temp3, temp4, temp5)
                if temp != -1:
                    temp1 = self.value.rfind('━', 0, temp)
                    temp2 = self.value.rfind('┗', 0, temp)
                    temp3 = self.value.rfind('┛', 0, temp)
                    if max(temp1, temp2, temp3) != -1:
                        temp = max([n for n in (temp1, temp2, temp3) if n >= 0])
                        temp1 = self.value.rfind(' ', 0, temp)
                        temp2 = self.value.rfind('╌', 0, temp)
                        temp3 = self.value.rfind('┄', 0, temp)
                        temp4 = self.value.rfind('┗', 0, temp)
                        temp5 = self.value.rfind('┛', 0, temp)
                        temp = max(temp1, temp2, temp3, temp4, temp5)
                        if temp == -1:
                            self.cursor_position = 0
                        else:
                            self.cursor_position = temp if self.value[temp] in ['┗', '┛'] else temp + 1
                    else:
                        self.parent.parent.parent.parent.parent.parent.parent.parent.previous_line()
                else:
                    self.parent.parent.parent.parent.parent.parent.parent.parent.previous_line()
                self.update_info_bar()
            event.stop()
            assert event.character is not None
            event.prevent_default()

    def _on_focus(self, event: events.Focus) -> None:
        self.cursor_position = 0
        if self.cursor_blink:
            self._blink_timer.resume()
        self.app.cursor_position = self.cursor_screen_offset
        self.has_focus = True
        self.refresh()
        if self.parent is not None:
            self.parent.post_message(events.DescendantFocus(self))
        self.update_info_bar()
        self.parent.parent.parent.parent.parent.parent.parent.parent.query_one("#explanations-keys").update(
            """[gold3]ctrl+c[/gold3]: close app  [gold3]ctrl+s[/gold3]: send request  [gold3]esc[/gold3]: cancel request  [gold3]up/down/pgUp/pgDown[/gold3]: scroll up/down if in scrollable window
            [gold3]t[/gold3]: toggle results view           [gold3]tab/shif+tab[/gold3]: jump to next/previous channel            [gold3]ctrl+t/ctrl+b[/gold3]: jump to top/bottom channel
            [gold3]right/left[/gold3]: move cursor on line  [gold3]home/end[/gold3]: jump to beginning/end of line                [gold3]n/p[/gold3]: jump to next/previous trace
            [gold3]c[/gold3]: capture NSLC under cursor     [gold3]s/e[/gold3]: capture timestamp under cursor as Start/End Time  [gold3]z[/gold3]: capture time span under cursor as Start and End Time
            Quality codes colors: [orange1][b]D[/b][/orange1] [green1][b]R[/b][/green1] [orchid][b]Q[/b][/orchid] [turquoise4][b]M[/b][/turquoise4]    Restriction policy: [i]empty[/i]/┄/[red1][b]R[/b][/red1] (open/unknown/restricted)""",
        )
        event.prevent_default()

    def _on_blur(self, event: events.Blur) -> None:
        super()._on_blur(event)
        try:
            self.parent.parent.parent.parent.parent.parent.parent.parent.query_one("#explanations-keys").update(
                """[gold3]ctrl+c[/gold3]: close app  [gold3]tab/shif+tab[/gold3]: cycle through options  [gold3]ctrl+s[/gold3]: send request  [gold3]esc[/gold3]: cancel request
                [gold3]up/down/pgUp/pgDown[/gold3]: scroll up/down if in scrollable window""")
        except:
            pass

    def _on_paste(self, event: events.Paste) -> None:
        event.stop()
        event.prevent_default()

    def action_cursor_right(self) -> None:
        super().action_cursor_right()
        if self.cursor_position >= len(self.value):
            self.cursor_position = len(self.value) - 1
        self.update_info_bar()

    def action_cursor_left(self) -> None:
        super().action_cursor_left()
        self.update_info_bar()

    def action_home(self) -> None:
        self.cursor_position = 0
        self.update_info_bar()

    def action_end(self) -> None:
        self.cursor_position = len(self.value) - 1
        self.update_info_bar()

    async def _on_click(self, event: events.Click) -> None:
        offset = event.get_content_offset(self)
        if offset is None:
            return
        event.stop()
        click_x = offset.x + self.view_position
        cell_offset = 0
        _cell_size = get_character_cell_size
        for index, char in enumerate(self.value):
            cell_width = _cell_size(char)
            if cell_offset <= click_x < (cell_offset + cell_width):
                self.cursor_position = index
                break
            cell_offset += cell_width
        else:
            self.cursor_position = len(self.value) - 1
        self.update_info_bar()

    def action_delete_right(self) -> None:
        pass

    def action_delete_right_word(self) -> None:
        pass

    def action_delete_right_all(self) -> None:
        pass

    def action_delete_left(self) -> None:
        pass

    def action_delete_left_word(self) -> None:
        pass

    def action_delete_left_all(self) -> None:
        pass
