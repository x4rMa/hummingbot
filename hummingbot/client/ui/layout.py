from os.path import dirname, join, realpath
from prompt_toolkit.layout.containers import (
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Box, Button, SearchToolbar

from hummingbot.client.ui.custom_widgets import CustomTextArea, FormattedCustomTextArea
from hummingbot.client.settings import (
    MAXIMUM_OUTPUT_PANE_LINE_COUNT,
    MAXIMUM_LOG_PANE_LINE_COUNT,
)


HEADER = """
                                                *,.
                                                *,,,*
                                            ,,,,,,,               *
                                            ,,,,,,,,            ,,,,
                                            *,,,,,,,,(        .,,,,,,
                                        /,,,,,,,,,,     .*,,,,,,,,
                                        .,,,,,,,,,,,.  ,,,,,,,,,,,*
                                        ,,,,,,,,,,,,,,,,,,,,,,,,,,,
                            //      ,,,,,,,,,,,,,,,,,,,,,,,,,,,,#*%
                        .,,,,,,,,. *,,,,,,,,,,,,,,,,,,,,,,,,,,,%%%%%%&@
                        ,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,%%%%%%%&
                    ,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,%%%%%%%&
                    /*,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,(((((%%&
                **.         #,,,,,,,,,,,,,,,,,,,,,,,,,,,,,((((((((((#.
            **               *,,,,,,,,,,,,,,,,,,,,,,,,**/(((((((((((((*
                                ,,,,,,,,,,,,,,,,,,,,*********((((((((((((
                                ,,,,,,,,,,,,,,,**************((((((((@
                                (,,,,,,,,,,,,,,,***************(#
                                    *,,,,,,,,,,,,,,,,**************/
                                    ,,,,,,,,,,,,,,,***************/
                                        ,,,,,,,,,,,,,,****************
                                        .,,,,,,,,,,,,**************/
                                            ,,,,,,,,*******,
                                            *,,,,,,,,********
                                            ,,,,,,,,,/******/
                                            ,,,,,,,,,@  /****/
                                            ,,,,,,,,
                                            , */


██   ██ ██    ██ ███    ███ ███    ███ ██ ███    ██  ██████  ██████   ██████  ████████
██   ██ ██    ██ ████  ████ ████  ████ ██ ████   ██ ██       ██   ██ ██    ██    ██
███████ ██    ██ ██ ████ ██ ██ ████ ██ ██ ██ ██  ██ ██   ███ ██████  ██    ██    ██
██   ██ ██    ██ ██  ██  ██ ██  ██  ██ ██ ██  ██ ██ ██    ██ ██   ██ ██    ██    ██
██   ██  ██████  ██      ██ ██      ██ ██ ██   ████  ██████  ██████   ██████     ██

=======================================================================================
Welcome to Hummingbot, an open source software client that helps you build and run
high-frequency trading (HFT) bots.

Helpful Links:
- Get 24/7 support: https://discord.hummingbot.io
- Learn how to use Hummingbot: https://docs.hummingbot.io
- Earn liquidity rewards: https://miner.hummingbot.io

Useful Commands:
- connect     List available exchanges and add API keys to them
- create      Create a new bot
- import      Import an existing bot by loading the configuration file
- help        List available commands

"""

with open(realpath(join(dirname(__file__), '../../VERSION'))) as version_file:
    version = version_file.read().strip()


def create_input_field(lexer=None, completer: Completer = None):
    return CustomTextArea(
        height=10,
        prompt='>>> ',
        style='class:input-field',
        multiline=False,
        focus_on_click=True,
        lexer=lexer,
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
        complete_while_typing=True,
    )


def create_output_field():
    return FormattedCustomTextArea(
        style='class:output-field',
        focus_on_click=False,
        read_only=False,
        scrollbar=True,
        max_line_count=MAXIMUM_OUTPUT_PANE_LINE_COUNT,
        initial_text=HEADER,
    )


def create_timer():
    return CustomTextArea(
        style='class:footer',
        focus_on_click=False,
        read_only=False,
        scrollbar=False,
        max_line_count=1,
        width=20,
    )


def create_process_monitor():
    return CustomTextArea(
        style='class:footer',
        focus_on_click=False,
        read_only=False,
        scrollbar=False,
        max_line_count=1,
        align=WindowAlign.RIGHT
    )


def create_trade_monitor():
    return CustomTextArea(
        style='class:footer',
        focus_on_click=False,
        read_only=False,
        scrollbar=False,
        max_line_count=1,
    )


def create_search_field() -> SearchToolbar:
    return SearchToolbar(text_if_not_searching=[('class:primary', "[CTRL + F] to start searching.")],
                         forward_search_prompt=[('class:primary', "Search logs [Press CTRL + F to hide search] >>> ")],
                         ignore_case=True)


def create_log_field(search_field: SearchToolbar):
    return CustomTextArea(
        style='class:log-field',
        text="Running logs\n",
        focus_on_click=False,
        read_only=False,
        scrollbar=True,
        max_line_count=MAXIMUM_LOG_PANE_LINE_COUNT,
        initial_text="Running Logs \n",
        search_field=search_field,
        preview_search=False,
    )


def create_log_toggle(function):
    return Button(
        text='> log pane',
        width=13,
        handler=function,
        left_symbol='',
        right_symbol=''
    )


def get_version():
    return [("class:header", f"Version: {version}")]


def get_paper_trade_status():
    from hummingbot.client.config.global_config_map import global_config_map
    enabled = global_config_map["paper_trade_enabled"].value is True
    paper_trade_status = "ON" if enabled else "OFF"
    style = "class:primary" if enabled else "class:log-field"
    return [(style, f"paper_trade_mode: {paper_trade_status}")]


def get_active_strategy():
    from hummingbot.client.hummingbot_application import HummingbotApplication
    hb = HummingbotApplication.main_application()
    style = "class:log-field"
    return [(style, f"Strategy: {hb.strategy_name}")]


"""def get_active_markets():
    from hummingbot.client.hummingbot_application import HummingbotApplication
    hb = HummingbotApplication.main_application()
    style = "class:primary"
    markets = "None" if len(hb.market_trading_pairs_map) == 0 \
              else eval(str(hb.market_trading_pairs_map))
    return [(style, f"Market(s): {markets}")]"""


"""def get_script_file():
    from hummingbot.client.config.global_config_map import global_config_map
    script = global_config_map["script_file_path"].value
    style = "class:primary"
    return [(style, f"Script_file: {script}")]"""


def get_strategy_file():
    from hummingbot.client.hummingbot_application import HummingbotApplication
    hb = HummingbotApplication.main_application()
    style = "class:log-field"
    return [(style, f"Strategy File: {hb._strategy_file_name}")]


def generate_layout(input_field: CustomTextArea,
                    output_field: CustomTextArea,
                    log_field: CustomTextArea,
                    log_toggle: Button,
                    search_field: SearchToolbar,
                    timer: CustomTextArea,
                    process_monitor: CustomTextArea,
                    trade_monitor: CustomTextArea):
    components = {}
    components["item_top_version"] = Window(FormattedTextControl(get_version), style="class:header")
    components["item_top_paper"] = Window(FormattedTextControl(get_paper_trade_status), style="class:header")
    components["item_top_active"] = Window(FormattedTextControl(get_active_strategy), style="class:header")
    # Window(FormattedTextControl(get_active_markets), style="class:header"),
    # Window(FormattedTextControl(get_script_file), style="class:header"),
    components["item_top_file"] = Window(FormattedTextControl(get_strategy_file), style="class:header")
    components["item_top_toggle"] = log_toggle
    components["pane_top"] = VSplit([components["item_top_version"],
                                     components["item_top_paper"],
                                     components["item_top_active"],
                                     components["item_top_file"],
                                     components["item_top_toggle"]], height=1)
    components["pane_bottom"] = VSplit([trade_monitor,
                                        process_monitor,
                                        timer], height=1)
    output_pane = Box(body=output_field, padding=0, padding_left=2, style="class:output-field")
    input_pane = Box(body=input_field, padding=0, padding_left=2, padding_top=1, style="class:input-field")
    components["pane_left"] = HSplit([output_pane,
                                      input_pane])
    right_pane = Box(body=HSplit([log_field, search_field]), padding=0, padding_left=2, style="class:log-field")
    components["pane_right"] = HSplit([right_pane])
    components["hint_menus"] = [Float(xcursor=True,
                                      ycursor=True,
                                      transparent=True,
                                      content=CompletionsMenu(max_height=16,
                                                              scroll_offset=1))]

    root_container = HSplit([
        components["pane_top"],
        VSplit(
            [FloatContainer(components["pane_left"], components["hint_menus"]),
             components["pane_right"]]),
        components["pane_bottom"],
    ])
    return Layout(root_container, focused_element=input_field), components
