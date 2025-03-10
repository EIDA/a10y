from textual.app import App
from textual.widgets import Header, Footer, Checkbox, Select, Input, Button, Collapsible, ContentSwitcher,Static,Label
from textual.containers import ScrollableContainer , Container, Horizontal
from a10y.widgets import Explanations, Requests, Results, Status, CursoredText # Import modular widgets
import requests
from datetime import datetime, timedelta
from textual.binding import Binding
from textual_autocomplete import DropdownItem
from textual.app import ComposeResult
from textual import work
from textual.worker import get_current_worker
import math
import os
import sys
import json
import threading
from pathlib import Path
from appdirs import user_cache_dir
from urllib.parse import urlparse
from a10y import __version__
CACHE_DIR = Path(user_cache_dir("a10y"))
CACHE_FILE = CACHE_DIR / "nodes_cache.json"
QUERY_URL = "https://www.orfeus-eu.org/eidaws/routing/1/globalconfig?format=fdsn"

class AvailabilityUI(App):
    def __init__(self, nodes_urls, routing, **kwargs):
        self.nodes_urls = nodes_urls  # Store nodes for later use
        self.routing = routing  # Store routing URL
        self.config = kwargs  # Store remaining settings
        super().__init__()  
    
    def action_quit(self) -> None:
        """Ensure terminal resets properly when quitting."""
        self.exit()
        if sys.platform == "win32":
            os.system("cls")  # Windows: Clear terminal
        else:
            os.system("reset")  # Linux/macOS: Reset terminal

    CSS_PATH = "a10y.tcss"
    BINDINGS = [
        
        Binding("ctrl+c", "quit", "Quit"),
        Binding("tab/shift+tab", "navigate", "Navigate"),
        Binding("ctrl+s", "send_button", "Send Request"),
        Binding("?", "toggle_help", "Help"),
        Binding("Submit Issues", "", "https://github.com/EIDA/a10y/issues",show=True),        
        Binding("Version","",f"{__version__}"),
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
            Requests(self.nodes_urls, self.config, classes="box"),  # Pass config
            Collapsible(Status(), title="Status", classes="box", id="status-collapse"),
            Results(classes="box", id="results-widget"),
            id="application-container"
        )
        yield Footer()
    def fetch_nodes_from_api(self):
        """Fetch fresh nodes from API and update cache."""
        nodes_urls = []
        try:
            response = requests.get(QUERY_URL, timeout=60)
            response.raise_for_status()
            data = response.json()

            for node in data.get("datacenters", []):
                node_name = node["name"]
                fdsnws_url = None

                for repo in node.get("repositories", []):
                    for service in repo.get("services", []):
                        if service["name"] == "fdsnws-station-1":
                            fdsnws_url = service["url"]
                            break
                    if fdsnws_url:
                        break

                if fdsnws_url:
                    parsed_url = urlparse(fdsnws_url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/fdsnws/"
                    nodes_urls.append((node_name, base_url, True))

            if nodes_urls:
                self.save_nodes_to_cache(nodes_urls)
        except requests.RequestException:
            pass
        finally:
            self.exit()

    def save_nodes_to_cache(self, nodes):
        """Save nodes to cache file permanently (no expiration)."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"nodes": nodes}, f)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Toggle between 'Select all' and 'Deselect all' when the checkbox is clicked."""
        all_nodes_checkbox = self.query_one("#all-nodes")  # Get the checkbox widget
        nodes_list = self.query_one("#nodes")  # Get the nodes list

        if all_nodes_checkbox.value:
            nodes_list.deselect_all()
            all_nodes_checkbox.label = "Select all"  # ✅ Change to "Select all"
        else:
            nodes_list.select_all()
            all_nodes_checkbox.label = "Deselect all"  # ✅ Change to "Deselect all"
        
        all_nodes_checkbox.refresh()  # ✅ Force UI update


        
        
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
    def on_input_changed(self, event: Input.Changed) -> None:
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
            self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\nRetrieving routing info from {self.routing}service=station&format=post{"&net="+net if net else ""}')
            self.query_one("#status-container").scroll_end()
            r = requests.get(f'{self.routing}service=station&format=post{"&net="+net if net else ""}')
            if r.status_code != 200:
                self.call_from_thread(lambda: self.change_button_disabled(False))
                self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[red]Couldn\'t retrieve routing info from {self.routing}service=station&format=post{"&net="+net if net else ""}[/red]')
                self.query_one("#status-container").scroll_end()
            else:
                self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[green]Retrieved routing info from {self.routing}service=station&format=post{"&net="+net if net else ""}[/green]')
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
            self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\nRetrieving routing info from {self.routing}service=station&format=post{"&net="+net if net else ""}{"&sta="+sta if sta else ""}')
            self.query_one("#status-container").scroll_end()
            r = requests.get(f'{self.routing}service=station&format=post{"&net="+net if net else ""}{"&sta="+sta if sta else ""}')
            if r.status_code != 200:
                self.call_from_thread(lambda: self.change_button_disabled(False))
                self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[red]Couldn\'t retrieve routing info from {self.routing}service=station&format=post{"&net="+net if net else ""}{"&sta="+sta if sta else ""}[/red]')
                self.query_one("#status-container").scroll_end()
            else:
                self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[green]Retrieved routing info from {self.routing}service=station&format=json{"&net="+net if net else ""}{"&sta="+sta if sta else ""}[/green]')
                self.query_one("#status-container").scroll_end()
                for line in r.text.splitlines()+['']:
                    if line.startswith('http'):
                        data = ''
                        url = line
                    elif line == "" and any([url.startswith(node_url) for node_url in self.query_one("#nodes").selected]):
                        self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\nRetrieving Channels from {url}')
                        r = requests.post(url, data=f'format=text\nlevel=channel\n{data}')
                        if r.status_code != 200:
                            self.call_from_thread(lambda: self.change_button_disabled(False))
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
            self.call_from_thread(lambda: self.change_button_disabled(False))
            self.query_one('#status-line').update(f'{self.query_one("#status-line").renderable}\n[red]No data available from {url}[/red]')
            if "hide" not in self.query_one("#loading").classes:
                self.query_one("#loading").add_class("hide")
        elif r.status_code != 200:
            self.call_from_thread(lambda: self.change_button_disabled(False))
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
    def change_button_disabled(self, disabled: bool) -> None:
        """Enable or disable the button safely in the main thread."""
        try:
            button = self.query_one("#request-button")
            button.disabled = disabled
            button.refresh()  # Force UI update
        except Exception as e:
            print(f"Error: {e}")

    @work(exclusive=True, thread=True)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        self.call_from_thread(lambda: self.change_button_disabled(True))
        # Disable the button to prevent multiple clicks
        if event.button.id == "reload-nodes":
            button = self.query_one("#reload-nodes")
            button.label = "Reloading..."
            button.disabled = True
            self.fetch_nodes_from_api()
        try:
            start = self.query_one("#start").value
            end = self.query_one("#end").value
            if not start.strip():
                self.query_one("#status-line").update("[red]Error: Start time is required![/red]")
                self.call_from_thread(lambda: self.change_button_disabled(False))
                return  # Stop execution if invalid

            if not end.strip():
                self.query_one("#status-line").update("[red]Error: End time is required![/red]")
                self.call_from_thread(lambda: self.change_button_disabled(False))
                return  # Stop execution if invalid


            self.query_one("#status-line").update("[green]Sending request...[/green]")
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
                self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\nRetrieving routing info from {self.routing}service=availability{params}')
                self.query_one("#status-container").scroll_end()
                r = requests.get(f'{self.routing}service=availability{params}')
                if r.status_code != 200:
                    self.call_from_thread(lambda: self.change_button_disabled(False)) 
                    self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[red]Couldn\'t retrieve routing info from {self.routing}service=availability{params}[/red]')
                    self.query_one("#status-container").scroll_end()
                    self.query_one("#loading").add_class("hide")
                else:
                    self.query_one("#status-line").update(f'{self.query_one("#status-line").renderable}\n[green]Retrieved routing info from {self.routing}service=availability{params}[/green]')
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
                        self.call_from_thread(lambda: self.change_button_disabled(False))
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
            
        
        finally:
            pass
        

    async def show_results(self, r):
        """The function responsible for drawing and showing the timelines"""
        csv_results = r.text
        request = r.request
        if not self.query(ContentSwitcher):
            await self.query_one('#results-widget').mount(ContentSwitcher(Container(id="lines"), ScrollableContainer(Static(id="plain"), id="plain-container"), initial="lines"))
            infoBar = Static("Quality:     Timestamp:                       Trace start:                       Trace end:                    ", id="info-bar")
            self.query_one('#lines').mount(infoBar)
            self.query_one('#lines').mount(ScrollableContainer(id="results-container"))
            # Dynamically calculate num_spans based on the results container width
            num_spans = self.query_one("#results-widget").size.width // 2  # Scale width properly
            num_spans = max(num_spans, 160)  # Ensure a reasonable span count


        if not self.query_one("#start").value.strip():
            self.query_one("#status-line").update(
                f"{self.query_one('#status-line').renderable}\n[orange1]⚠️ Please enter a start date![/orange1]"
            )
            return 
        if not self.query_one("#end").value.strip():
            self.query_one("#status-line").update(
                f"{self.query_one('#status-line').renderable}\n[orange1]⚠️ Please enter an end date![/orange1]"
            )
            return  # Stop execution if the end date is missing
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
            self.call_from_thread(lambda: self.change_button_disabled(False))
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
