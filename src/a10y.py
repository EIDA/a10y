from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Static, Label, Select, Input, Checkbox, Button, ContentSwitcher, Collapsible, LoadingIndicator, SelectionList
from textual.binding import Binding
from textual_autocomplete import AutoComplete, Dropdown, DropdownItem
from textual import work
from textual.worker import get_current_worker
import requests
from datetime import datetime, timedelta
from rich.text import Text
from rich.cells import get_character_cell_size
import os
import sys
import logging
import argparse
from textual.suggester import Suggester
import math
import tomli

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


class Explanations(Static):
    """Explanations box with common key functions"""

    def compose(self) -> ComposeResult:
        yield Static("[b]Useful Keys[/b]")
        yield Static(
            """[gold3]ctrl+c[/gold3]: close app  [gold3]tab/shif+tab[/gold3]: cycle through options  [gold3]ctrl+s[/gold3]: send request  [gold3]esc[/gold3]: cancel request
            [gold3]up/down/pgUp/pgDown[/gold3]: scroll up/down if in scrollable window""",
            id="explanations-keys")


class Requests(Static):
    """Web service request control widget"""

    def compose(self) -> ComposeResult:
        yield Static("[b]Requests Control[/b]", id="request-title")
        yield Container(
            Checkbox("Select all Nodes", True, id="all-nodes"),
            SelectionList(*nodesUrls, id="nodes"),
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
            Input(classes="date-input", id="start", value=default_starttime),
            Label("End Time:", classes="request-label"),
            Input(classes="date-input", id="end", value=default_endtime),
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
            Input(value=default_mergegaps, type="number", id="mergegaps"),
            Label("Merge Options:", classes="request-label"),
            Checkbox("Samplerate", default_merge_samplerate, id="samplerate"),
            Checkbox("Quality", default_merge_quality, id="qual"),
            Checkbox("Overlap", default_merge_overlap, id="overlap"),
            Label("Quality:", classes="request-label"),
            Checkbox("D", default_quality_D, id="qd"),
            Checkbox("R", default_quality_R, id="qr"),
            Checkbox("Q", default_quality_Q, id="qq"),
            Checkbox("M", default_quality_M, id="qm"),
            id="options"
        )
        yield Horizontal(
            Checkbox("Include Restricted", default_includerestricted, id="restricted"),
            Button("Send", variant="primary", id="request-button"),
            Input(placeholder="Enter POST file path", value=default_file, suggester=FileSuggester(), id="post-file"),
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


class AvailabilityUI(App):
    CSS_PATH = "a10y.css"
    BINDINGS = [
        Binding("ctlrl+c", "quit", "Quit"),
        Binding("tab/shift+tab", "navigate", "Navigate"),
        Binding("ctrl+s", "send_button", "Send Request"),
        Binding("?", "toggle_help", "Help"),
        Binding("Submit Issues", "", "https://github.com/EIDA/a10y/issues"),
        Binding("ctrl+t", "first_line", "Move to first line", show=False),
        Binding("ctrl+b", "last_line", "Move to last line", show=False),
        Binding("t", "lines_view", "Toggle view to lines", show=False),
        Binding("escape", "cancel_request", "Cancel request", show=False),
    ]

    req_text = ""

    def compose(self) -> ComposeResult:
        self.title = "Availability UI"
        yield Header()
        yield ScrollableContainer(
            Explanations(classes="box hide"),
            Requests(classes="box"),
            Collapsible(Status(), title="Status", classes="box", id="status-collapse"),
            Results(classes="box", id="results-widget"),
            id="application-container"
        )
        yield Footer()


    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """A function to select/deselect all nodes when corresponding checkbox is clicked"""
        if event.checkbox == self.query_one("#all-nodes"):
            if self.query_one("#all-nodes").value:
                self.query_one("#nodes").select_all()
            else:
                self.query_one("#nodes").deselect_all()


    def on_select_changed(self, event: Select.Changed) -> None:
        """A function to issue appropriate request and update status when a Node or when a common time frame is selected"""
        if event.select == self.query_one("#times"):
            start = self.query_one("#start")
            mergegaps = self.query_one("#mergegaps")
            if not event.value:
                start.value = ""
                end = self.query_one("#end")
                end.value = ""
                return None
            if event.value == 1:
                start.value = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
                mergegaps.value = "0.0"
            elif event.value == 2:
                start.value = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
                mergegaps.value = "0.0"
            elif event.value == 3:
                start.value = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
                mergegaps.value = "1.0"
            elif event.value == 4:
                start.value = datetime.now().replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S")
                if datetime.now().date().day > 7:
                    mergegaps.value = "5.0"
            elif event.value == 5:
                start.value = (datetime.now() - timedelta(days=61)).strftime("%Y-%m-%dT%H:%M:%S")
                mergegaps.value = "10.0"
            elif event.value == 6:
                start.value = (datetime.now() - timedelta(days=183)).strftime("%Y-%m-%dT%H:%M:%S")
                mergegaps.value = "60.0"
            elif event.value == 7:
                start.value = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S")
                if datetime.now().date().month >= 6:
                    mergegaps.value = "300.0"
            end = self.query_one("#end")
            end.value = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


    @work(thread=True)
    def parallel_requests_autocomplete(self, url, data) -> None:
        worker = get_current_worker()
        autocomplete = self.query_one("#stations")
        self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\nRetrieving Stations from {url}')
        r = requests.post(url, data=f'format=text\n{data}')
        if r.status_code != 200:
            self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[red]Couldn\'t retrieve Stations from {url}[/red]')
        else:
            self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[green]Retrieved Stations from {url}[/green]')
            autocomplete.items += [DropdownItem(s.split('|')[1]) for s in r.text.splitlines()[1:]]
        self.query_one("#status-container").scroll_end()


    @work(exclusive=True, thread=True)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """A function to change status when an NSLC input field is submitted (i.e. is typed and enter is hit)"""
        # COULD BE ON Change 
        # keep app responsive while making requests
        worker = get_current_worker()
        # for typing network
        if event.input == self.query_one("#network"):
            # clear previous results
            autocomplete = self.query_one("#stations")
            autocomplete.items = []
            # get available stations from routing system
            net = self.query_one('#network').value
            self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\nRetrieving routing info from {routing}service=station&format=post{"&net="+net if net else ""}')
            self.query_one("#status-container").scroll_end()
            r = requests.get(f'{routing}service=station&format=post{"&net="+net if net else ""}')
            if r.status_code != 200:
                self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[red]Couldn\'t retrieve routing info from {routing}service=station&format=post{"&net="+net if net else ""}[/red]')
                self.query_one("#status-container").scroll_end()
            else:
                self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[green]Retrieved routing info from {routing}service=station&format=post{"&net="+net if net else ""}[/green]')
                self.query_one("#status-container").scroll_end()
                for line in r.text.splitlines()+['']:
                    if line.startswith('http'):
                        data = ''
                        url = line
                    elif line == "" and any([url.startswith(node_url) for node_url in self.query_one("#nodes").selected]):
                        if not worker.is_cancelled:
                            # execute the requests in parallel and in batches of 150
                            lines = data.splitlines()
                            batch_size = 150
                            for i in range(0, len(lines), batch_size):
                                batch_data = '\n'.join(lines[i:i+batch_size])
                                self.parallel_requests_autocomplete(url, batch_data)
                    else:
                        data += f"{' '.join(line.split()[:4])} 1800-01-01 2200-12-31\n"
        # for typing station
        elif event.input == self.query_one("#station"):
            # clear previous results
            autocomplete = self.query_one("#channels")
            autocomplete.items = []
            # get available channels from FDSN
            net = self.query_one('#network').value
            sta = self.query_one('#station').value
            self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\nRetrieving routing info from {routing}service=station&format=post{"&net="+net if net else ""}{"&sta="+sta if sta else ""}')
            self.query_one("#status-container").scroll_end()
            r = requests.get(f'{routing}service=station&format=post{"&net="+net if net else ""}{"&sta="+sta if sta else ""}')
            if r.status_code != 200:
                self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[red]Couldn\'t retrieve routing info from {routing}service=station&format=post{"&net="+net if net else ""}{"&sta="+sta if sta else ""}[/red]')
                self.query_one("#status-container").scroll_end()
            else:
                self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[green]Retrieved routing info from {routing}service=station&format=json{"&net="+net if net else ""}{"&sta="+sta if sta else ""}[/green]')
                self.query_one("#status-container").scroll_end()
                for line in r.text.splitlines()+['']:
                    if line.startswith('http'):
                        data = ''
                        url = line
                    elif line == "" and any([url.startswith(node_url) for node_url in self.query_one("#nodes").selected]):
                        self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\nRetrieving Channels from {url}')
                        r = requests.post(url, data=f'format=text\nlevel=channel\n{data}')
                        if r.status_code != 200:
                            self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[red]Couldn\'t retrieve Channels from {url}[/red]')
                            self.query_one("#status-container").scroll_end()
                        else:
                            self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[green]Retrieved Channels from {url}[/green]')
                            self.query_one("#status-container").scroll_end()
                            autocomplete.items += [DropdownItem(unique) for unique in {c.split('|')[3] for c in r.text.splitlines()[1:]}]
                    else:
                        data += f'{line}\n'


    @work(thread=True)
    def parallel_requests_availability(self, url, data) -> None:
        worker = get_current_worker()
        merge = ",".join([option for option, bool in zip(['samplerate', 'quality', 'overlap'], [self.query_one("#samplerate").value, self.query_one("#qual").value, self.query_one("#overlap").value]) if bool])
        mergegaps = str(self.query_one("#mergegaps").value)
        quality = ",".join([q for q, bool in zip(['D', 'R', 'Q', 'M'], [self.query_one("#qd").value, self.query_one("#qr").value, self.query_one("#qq").value, self.query_one("#qm").value]) if bool])
        restricted = self.query_one("#restricted").value
        self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\nIssuing request to {url}')
        self.query_one("#status-container").scroll_end()
        r = requests.post(url, data=f'{"quality="+quality if quality else ""}\n{"mergegaps="+mergegaps if mergegaps else ""}\nformat=geocsv\n{"merge="+merge if merge else ""}\n{"includerestricted=TRUE" if restricted else ""}\n{data}')
        if r.status_code == 204:
            self.query_one('#status-line').update(f'{self.query_one("#status-line").renderable}\n[red]No data available from {url}[/red]')
            if "hide" not in self.query_one("#loading").classes:
                self.query_one("#loading").add_class("hide")
        elif r.status_code != 200:
            self.query_one('#status-line').update(f'{self.query_one("#status-line").renderable}\n[red]Request to {url} failed. See below for more details[/red]')
            self.query_one("#error-results").remove_class("hide")
            self.query_one("#error-results").update(f'[red]{self.query_one("#error-results").renderable}\n{r.text}[/red]')
            self.query_one("#error-results").scroll_end()
            if "hide" not in self.query_one("#loading").classes:
                self.query_one("#loading").add_class("hide")
        else:
            self.query_one('#status-line').update(f'{self.query_one("#status-line").renderable}\n[green]Request to {url} successfully returned data[/green]')
            self.req_text += f'\n{r.text}'
            self.call_from_thread(self.show_results, r)
        self.query_one("#status-container").scroll_end()


    @work(exclusive=True, thread=True)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """A function to send availability request when Send button is clicked"""
        worker = get_current_worker()
        # clear previous results
        self.req_text = ""
        if self.query(ContentSwitcher):
            self.query_one(ContentSwitcher).remove()
        self.query_one("#error-results").update("")
        self.query_one("#error-results").add_class("hide")
        # show loading indicator in results
        self.query_one("#loading").remove_class("hide")
        # build request
        net = self.query_one("#network").value
        sta = self.query_one("#station").value
        loc = self.query_one("#location").value
        cha = self.query_one("#channel").value
        start = self.query_one("#start").value
        end = self.query_one("#end").value
        # request from send button
        if event.button == self.query_one("#request-button"):
            params = f"&format=post{'&net='+net if net else ''}{'&sta='+sta if sta else ''}{'&loc='+loc if loc else ''}{'&cha='+cha if cha else ''}{'&start='+start if start else ''}{'&end='+end if end else ''}"
            self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\nRetrieving routing info from {routing}service=availability{params}')
            self.query_one("#status-container").scroll_end()
            r = requests.get(f'{routing}service=availability{params}')
            if r.status_code != 200:
                self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[red]Couldn\'t retrieve routing info from {routing}service=availability{params}[/red]')
                self.query_one("#status-container").scroll_end()
                self.query_one("#loading").add_class("hide")
            else:
                self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[green]Retrieved routing info from {routing}service=availability{params}[/green]')
                self.query_one("#status-container").scroll_end()
                at_least_one = False
                for line in r.text.splitlines()+['']:
                    if line.startswith('http'):
                        data = ''
                        url = line
                    elif line == "" and any([url.startswith(node_url) for node_url in self.query_one("#nodes").selected]):
                        if not worker.is_cancelled:
                            at_least_one = True
                            # execute the requests in parallel and in batches of 100
                            lines = data.splitlines()
                            batch_size = 100
                            for i in range(0, len(lines), batch_size):
                                batch_data = '\n'.join(lines[i:i+batch_size])
                                self.parallel_requests_availability(url, batch_data)
                    else:
                        data += f'{line}\n'
                if not at_least_one:
                    self.query_one('#status-line').update(f'{self.query_one("#status-line").renderable}\n[red]No data available[/red]')
                    self.query_one("#status-container").scroll_end()
                    if "hide" not in self.query_one("#loading").classes:
                        self.query_one("#loading").add_class("hide")
        # request from file button
        elif event.button == self.query_one("#file-button"):
            filename = self.query_one("#post-file").value
            if os.path.isfile(filename):
                self.query_one('#status-line').update(f'{self.query_one("#status-line").renderable}\nReading NSLC from file {filename}')
                self.query_one("#status-container").scroll_end()
                data = ''
                with open(filename, 'r') as f:
                    for l in f.readlines():
                        if '=' not in l:
                            data += f"{' '.join(l.split()[:4])} {start} {end}\n"
                for url in self.query_one("#nodes").selected:
                    if not worker.is_cancelled:
                        self.parallel_requests_availability(url+'availability/1/query', data)


    async def show_results(self, r):
        """The function responsible for drawing and showing the timelines"""
        csv_results = r.text
        request = r.request
        if not self.query(ContentSwitcher):
            await self.query_one('#results-widget').mount(ContentSwitcher(Container(id="lines"), ScrollableContainer(Static(id="plain"), id="plain-container"), initial="lines"))
            infoBar = Static("Quality:     Timestamp:                       Trace start:                       Trace end:                    ", id="info-bar")
            self.query_one('#lines').mount(infoBar)
            self.query_one('#lines').mount(ScrollableContainer(id="results-container"))
        # cut time frame into desired number of spans
        num_spans = 130
        try:
            start_frame = datetime.strptime(self.query_one("#start").value, "%Y-%m-%dT%H:%M:%S")
        except:
            start_frame = datetime.strptime(self.query_one("#start").value+"T00:00:00", "%Y-%m-%dT%H:%M:%S")
        try:
            end_frame = datetime.strptime(self.query_one("#end").value, "%Y-%m-%dT%H:%M:%S")
        except:
            end_frame = datetime.strptime(self.query_one("#end").value+"T00:00:00", "%Y-%m-%dT%H:%M:%S")
        span_frame = (end_frame - start_frame) / num_spans
        lines = {} # for lines of each nslc, contains line characters
        infos = {} # for the info-bar of each nslc, contains a list of lists (one inner list for each span) for each channel; inner lists format: [quality/gaps, timestamp, trace_start, trace_end, span_start, span_end]
        csv_results = csv_results.splitlines()[5:]
        for row in csv_results:
            parts = row.split('|')
            key = f"{parts[0]}_{parts[1]}_{parts[2]}_{parts[3]}"
            # initialization
            if key not in lines:
                lines[key] = [' ' for i in range(num_spans)]
                infos[key] = [["", "", "", "", "", ""] for i in range(num_spans)]
                for i in range(num_spans):
                    infos[key][i][1] = (start_frame+(i+0.5)*span_frame).strftime("%Y-%m-%dT%H:%M:%S")  # timestamp in the middle of each span
                    infos[key][i][4] = start_frame + i * span_frame
                    infos[key][i][5] = end_frame if i == num_spans - 1 else start_frame + (i + 1) * span_frame
            start_trace = datetime.strptime(parts[6], "%Y-%m-%dT%H:%M:%S.%fZ")
            end_trace = datetime.strptime(parts[7], "%Y-%m-%dT%H:%M:%S.%fZ")
            first_span = math.floor((start_trace-start_frame) / span_frame)
            last_span = min(math.ceil((end_trace-start_frame) / span_frame), num_spans)
            for i in range(first_span, last_span):
                if lines[key][i] == ' ':
                    char = '━'
                    if i == first_span and infos[key][i][4] < start_trace:
                        char = '┗'
                    elif i == last_span - 1 and end_trace < infos[key][i][5]:
                        char = '┛'
                    if parts[4] == 'D':
                        lines[key][i] = f'[orange1]{char}[/orange1]'
                        infos[key][i] = ['D', infos[key][i][1], start_trace.strftime("%Y-%m-%dT%H:%M:%S"), end_trace.strftime("%Y-%m-%dT%H:%M:%S"), infos[key][i][4], infos[key][i][5]]
                    elif parts[4] == 'R':
                        lines[key][i] = f'[green1]{char}[/green1]'
                        infos[key][i] = ['R', infos[key][i][1], start_trace.strftime("%Y-%m-%dT%H:%M:%S"), end_trace.strftime("%Y-%m-%dT%H:%M:%S"), infos[key][i][4], infos[key][i][5]]
                    elif parts[4] == 'Q':
                        lines[key][i] = f'[orchid]{char}[/orchid]'
                        infos[key][i] = ['Q', infos[key][i][1], start_trace.strftime("%Y-%m-%dT%H:%M:%S"), end_trace.strftime("%Y-%m-%dT%H:%M:%S"), infos[key][i][4], infos[key][i][5]]
                    elif parts[4] == 'M':
                        lines[key][i] = f'[turquoise4]{char}[/turquoise4]'
                        infos[key][i] = ['M', infos[key][i][1], start_trace.strftime("%Y-%m-%dT%H:%M:%S"), end_trace.strftime("%Y-%m-%dT%H:%M:%S"), infos[key][i][4], infos[key][i][5]]
                elif any(c in lines[key][i] for c in ['━', '┗', '┛']):
                    lines[key][i] = '╌'
                    # start of gap is the end of previously found trace in this span and end of gap is the start of the new trace
                    infos[key][i] = ['1', infos[key][i][1], infos[key][i][3], start_trace.strftime("%Y-%m-%dT%H:%M:%S"), infos[key][i][4], infos[key][i][5]]
                elif lines[key][i] == '╌' or lines[key][i] == '┄':
                    lines[key][i] = '┄'
                    # start of gaps is the start of the first gap in this span and end is the start of the new trace
                    infos[key][i] = [str(int(infos[key][i][0])+1), infos[key][i][1], infos[key][i][2], start_trace.strftime("%Y-%m-%dT%H:%M:%S"), infos[key][i][4], infos[key][i][5]]
        # longest possible label to align start of lines
        longest_label = 26
        for k in lines:
            infos[k].append(("", "", "", "", "", "")) # because cursor can go one character after the end of the input
            # add infos in long gaps
            # switched off because leads to O(num_spans*num_channels*len(csv_results)) complexity and makes app too slow for long availability output
            #for i in range(num_spans):
                #if lines[k][i] == ' ':
                    # long gap starts after the latest of the traces that exist before the current span
                    #infos[k][i][2] = max([datetime.strptime(row.split('|')[7], "%Y-%m-%dT%H:%M:%S.%fZ") for row in csv_results if datetime.strptime(row.split('|')[7], "%Y-%m-%dT%H:%M:%S.%fZ") < datetime.strptime(infos[k][i][1], "%Y-%m-%dT%H:%M:%S")] + [start_frame])
                    #infos[k][i][2] = infos[k][i][2].strftime("%Y-%m-%dT%H:%M:%S")
                    # long gap ends before the earliest of the traces that exist after the current span
                    #infos[k][i][3] = min([datetime.strptime(row.split('|')[6], "%Y-%m-%dT%H:%M:%S.%fZ") for row in csv_results if datetime.strptime(row.split('|')[6], "%Y-%m-%dT%H:%M:%S.%fZ") > datetime.strptime(infos[k][i][1], "%Y-%m-%dT%H:%M:%S")] + [end_frame])
                    #infos[k][i][3] = infos[k][i][3].strftime("%Y-%m-%dT%H:%M:%S")
            # add line in results
            await self.query_one('#results-container').mount(Horizontal(Label(f"{k} ┄{' '*(longest_label-len(k))}"), CursoredText(value=''.join(lines[k]), info=infos[k], id=f"_{k}"), classes="result-item"))
        if self.query(CursoredText):
            self.query(CursoredText)[0].focus()
        if "hide" not in self.query_one("#loading").classes:
            self.query_one("#loading").add_class("hide")
        # show restrictions info for each channel using /extent method of availability webservice
        self.show_restriction(request)


    @work(thread=True)
    def show_restriction(self, request):
        """A function for showing whether a channel is restricted or not"""
        worker = get_current_worker()
        new_url = request.url.replace("query", "extent")
        old_body = request.body.split('\n')
        filtered = [row for row in old_body if "mergegaps" not in row]
        new_body = '\n'.join(filtered)
        self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\nRetrieving restrictions info from {new_url}')
        r = requests.post(new_url, data=new_body)
        if r.status_code == 200:
            self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[green]Retrieved restrictions info from {new_url}[/green]')
            for line in r.text.splitlines()[5:]:
                parts = line.split('|')
                nslc = f"{parts[0]}_{parts[1]}_{parts[2]}_{parts[3]}"
                label_item = self.query_one(f"#_{nslc}").parent.query_one(Label)
                if parts[10] == "RESTRICTED":
                    label_item.update(f"{label_item.renderable[:len(nslc)+1]}[red1][b]R[/b][/red1]{label_item.renderable[len(nslc)+2:]}")
                else:
                    label_item.update(f"{label_item.renderable[:len(nslc)+1]} {label_item.renderable[len(nslc)+2:]}")


    def action_toggle_help(self) -> None:
        """An action for the user to show or hide useful keys box"""
        if "hide" in self.query_one(Explanations).classes:
            self.query_one(Explanations).remove_class("hide")
        else:
            self.query_one(Explanations).add_class("hide")


    def action_cancel_request(self) -> None:
        """An action for the user to cancel requests (if for example they take too much time)"""
        self.workers.cancel_all()


    def action_first_line(self) -> None:
        """An action to move focus to the first line"""
        if self.query(CursoredText):
            self.query(CursoredText)[0].focus()


    def action_last_line(self) -> None:
        """An action to move focus to the last line"""
        if self.query(CursoredText):
            self.query(CursoredText)[-1].focus()
            self.query_one("#application-container").scroll_end()


    def action_lines_view(self) -> None:
        if self.query(ContentSwitcher) and self.query_one(ContentSwitcher).current == "plain-container":
            self.query_one(ContentSwitcher).current = "lines"
            nslc_to_focus = '_'.join(str(self.query_one("#plain").renderable).splitlines()[-1].split('|')[:4])
            self.query_one(f"#_{nslc_to_focus}").focus()


    def action_send_button(self) -> None:
        """An action equivalent to pressing send button"""
        self.on_button_pressed(Button.Pressed(button=self.query_one("#request-button")))


    def next_line(self):
        self.action_focus_next()
        if self.focused not in self.query(CursoredText):
            self.query(CursoredText)[-1].focus()
            # below line does not have effect because focus turns out to happen after below line is executed
            #self.query(CursoredText)[-1].action_end()


    def previous_line(self):
        self.action_focus_previous()
        if self.focused not in self.query(CursoredText):
            self.query(CursoredText)[0].focus()
        else:
            # below line does not have effect because focus turns out to happen after below line is executed
            self.query(CursoredText)[0].action_end()


if __name__ == "__main__":
    # parse arguments
    def parse_arguments():
        desc = 'Availability UI application'
        parser = argparse.ArgumentParser(description=desc)
        parser.add_argument('-p', '--post', default = None,
                            help='Default file path for POST requests')
        parser.add_argument('-c', '--config', default = None,
                            help='Configuration file path')
        return parser.parse_args()

    args = parse_arguments()
    routing = 'https://www.orfeus-eu.org/eidaws/routing/1/query?'

    reqNodes = requests.get('https://orfeus-eu.org/epb/nodes')
    nodesUrls = []
    if reqNodes.status_code == 200:
        for n in reqNodes.json():
            nodesUrls.append((n['node_code'], f"https://{n['node_url_base']}/fdsnws/", True))
    else:
        nodesUrls = [
            ("GFZ", "https://geofon.gfz-potsdam.de/fdsnws/", True),
            ("ODC", "https://orfeus-eu.org/fdsnws/", True),
            ("ETHZ", "https://eida.ethz.ch/fdsnws/", True),
            ("RESIF", "https://ws.resif.fr/fdsnws/", True),
            ("INGV", "https://webservices.ingv.it/fdsnws/", True),
            ("LMU", "https://erde.geophysik.uni-muenchen.de/fdsnws/", True),
            ("ICGC", "https://ws.icgc.cat/fdsnws/", True),
            ("NOA", "https://eida.gein.noa.gr/fdsnws/", True),
            ("BGR", "https://eida.bgr.de/fdsnws/", True),
            ("BGS", "https://eida.bgs.ac.uk/fdsnws/", True),
            ("NIEP", "https://eida-sc3.infp.ro/fdsnws/", True),
            ("KOERI", "https://eida.koeri.boun.edu.tr/fdsnws/", True),
            ("UIB-NORSAR", "https://eida.geo.uib.no/fdsnws/", True)
        ]

    # use below defaults or take them from config file if exists
    default_file = args.post
    default_starttime = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
    default_endtime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    default_quality_D = True
    default_quality_R = True
    default_quality_Q = True
    default_quality_M = True
    default_mergegaps = "1.0"
    default_merge_samplerate = False
    default_merge_quality = False
    default_merge_overlap = True
    default_includerestricted = True

    if args.config is not None:
        config_file = args.config
    else:
        config_dir = os.getenv("XDG_CONFIG_DIR", "")
        if not config_dir:
            config_file = os.path.join(".", "config.toml")
        else:
            config_file = os.path.join(config_dir, "a10y", "config.toml")
    if os.path.isfile(config_file):
        with open(config_file, 'rb') as f:
            try:
                config = tomli.load(f)
            except:
                logging.error(f"Invalid format of config file {config_file}")
                sys.exit(1)
            # starttime
            parts = config['starttime'].split()
            try:
                num = int(parts[0])
                default_starttime = (datetime.now() - timedelta(days=num)).strftime("%Y-%m-%dT%H:%M:%S")
            except:
                try:
                    datetime.strptime(config['starttime'], "%Y-%m-%dT%H:%M:%S")
                    default_starttime = config['starttime']
                except:
                    logging.error(f"Invalid starttime format in config file {config_file}")
                    sys.exit(1)
            # endtime
            if config['endtime'] == "now":
                pass
            else:
                try:
                    datetime.strptime(config['endtime'], "%Y-%m-%dT%H:%M:%S")
                    default_endtime = config['endtime']
                except:
                    logging.error(f"Invalid endtime format in config file {config_file}")
                    sys.exit(1)
            # quality
            if any([q not in ['D', 'R', 'Q', 'M'] for q in config['quality']]):
                logging.error(f"Invalid quality codes format in config file {config_file}")
                sys.exit(1)
            if 'D' not in config['quality']:
                default_quality_D = False
            if 'R' not in config['quality']:
                default_quality_R = False
            if 'Q' not in config['quality']:
                default_quality_Q = False
            if 'M' not in config['quality']:
                default_quality_M = False
            # mergegaps
            try:
                num = float(config['mergegaps'])
            except:
                logging.error(f"Invalid mergegaps format in config file {config_file}")
                sys.exit(1)
            default_mergegaps = str(num)
            # merge
            if any([m not in ['samplerate', 'quality', 'overlap'] for m in config['merge']]):
                logging.error(f"Invalid merge options format in config file {config_file}")
                sys.exit(1)
            if 'samplerate' in config['merge']:
                default_merge_samplerate = True
            if 'quality' in config['merge']:
                default_merge_quality = True
            if 'overlap' not in config['merge']:
                default_merge_overlap = False
            # includerestricted
            if config['includerestricted'] == False:
                default_includerestricted = False
    elif args.config is not None:
        logging.error(f"Config file '{config_file}' not found")
        sys.exit(1)

    app = AvailabilityUI()
    app.run()
