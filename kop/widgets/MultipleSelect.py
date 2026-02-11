from textual import on
from textual import events
from textual.app import ComposeResult
from textual.message import Message
from textual.timer import Timer
from textual.reactive import var
from textual.containers import Vertical
from textual.widgets import SelectionList, OptionList
from textual.widgets._select import SelectCurrent
from textual.widgets._selection_list import SelectionType
from textual.widgets.selection_list import Selection
from textual.css.query import NoMatches
from textual.content import Content
from rich.text import Text
from dataclasses import dataclass
from typing import Generic




class MultipleSelectCurrent(SelectCurrent):
    ...


class MultipleSelectOverlay(SelectionList):
    """The 'pop-up' overlay for the MultipleSelect control."""

    BINDINGS = [("escape", "dismiss", "Dismiss menu")]

    @dataclass
    class Dismiss(Message):
        """Inform ancestor the overlay should be dismissed."""

        lost_focus: bool = False
        """True if the overlay lost focus."""

    @dataclass
    class UpdateSelection(Message):
        """Inform ancestor the selection was changed."""

        option_index: int
        """The index of the new selection."""

    def __init__(self, type_to_search: bool = True) -> None:
        super().__init__()
        self._type_to_search = type_to_search
        """If True (default), the user can type to search for a matching option and the cursor will jump to it."""

        self._search_query: str = ""
        """The current search query used to find a matching option and jump to it."""

        self._search_reset_delay: float = 0.7
        """The number of seconds to wait after the most recent key press before resetting the search query."""

    def on_mount(self) -> None:
        def reset_query() -> None:
            self._search_query = ""

        self._search_reset_timer = Timer(
            self, self._search_reset_delay, callback=reset_query
        )

    def watch_has_focus(self, value: bool) -> None:
        self._search_query = ""
        if value:
            self._search_reset_timer._start()
        else:
            self._search_reset_timer.reset()
            self._search_reset_timer.stop()
        super().watch_has_focus(value)

    async def _on_key(self, event: events.Key) -> None:
        if not self._type_to_search:
            return

        self._search_reset_timer.reset()

        if event.character is not None and event.is_printable:
            event.time = 0
            event.stop()
            event.prevent_default()

            # Update the search query and jump to the next option that matches.
            self._search_query += event.character
            index = self._find_search_match(self._search_query)
            if index is not None:
                # highlight the search matched item
                self.highlighted = index

    def check_consume_key(self, key: str, character: str | None = None) -> bool:
        """Check if the widget may consume the given key."""
        return (
            self._type_to_search and character is not None and character.isprintable()
        )

    def _find_search_match(self, query: str) -> int | None:
        """A simple substring search which favors options containing the substring
        earlier in the prompt.

        Args:
            query: The substring to search for.

        Returns:
            The index of the option that matches the query, or `None` if no match is found.
        """
        best_match: int | None = None
        minimum_index: int | None = None

        query = query.lower()
        for index, option in enumerate(self.options):
            prompt = option.prompt
            if isinstance(prompt, Content):
                prompt = prompt._text.lower()
            if isinstance(prompt, Text):
                lower_prompt = prompt.plain.lower()
            elif isinstance(prompt, str):
                lower_prompt = prompt.lower()
            else:
                continue

            match_index = lower_prompt.find(query)
            if match_index != -1 and (
                minimum_index is None or match_index < minimum_index
            ):
                best_match = index
                minimum_index = match_index

        return best_match

    def action_dismiss(self) -> None:
        """Dismiss the overlay."""
        self.post_message(self.Dismiss())

    def _on_blur(self, _event: events.Blur) -> None:
        """On blur we want to dismiss the overlay."""
        self.post_message(self.Dismiss(lost_focus=True))
        self.suppress_click()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Inform parent when an option is selected."""
        event.stop()
        self.post_message(self.UpdateSelection(event.option_index))

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        """Stop option list highlighted messages leaking."""
        event.stop()



class MultipleSelect(Generic[SelectionType], Vertical, can_focus=True):

    DEFAULT_CSS = """
    MultipleSelect {
        height: auto;
        color: $foreground;

        &.-textual-compact {
            & > SelectCurrent {
                padding: 0 1 0 0;
                border: none !important;
            }            
        }
        
        .up-arrow {
            display: none;
        }

        &:focus > MultipleSelectCurrent {
            border: tall $border;
            background-tint: $foreground 5%;
        }

        & > MultipleSelectOverlay {
            width: 1fr;
            display: none;
            height: auto;
            max-height: 12;
            overlay: screen;
            constrain: none inside;
            color: $foreground;
            border: tall $border-blurred;
            background: $surface;
            &:focus {
                background-tint: $foreground 5%;
            }
            & > .option-list--option {
                padding: 0 1;
            }
        }

        &.-expanded {
            .down-arrow {
                display: none;
            }
            .up-arrow {
                display: block;
            }
            & > MultipleSelectOverlay {
                display: block;
            }
        }

    }

    """

    expanded: var[bool] = var(False, init=False)
    """True to show the overlay, otherwise False."""
    prompt: var[str] = var[str]("Select")

    def __init__(self, *selections: Selection[SelectionType], prompt: str = "Select", **kwargs) -> None:
        super().__init__(**kwargs)
        self.selections = selections
        self.prompt = prompt
    
    def compose(self) -> ComposeResult:
        yield MultipleSelectCurrent(self.prompt)
        yield MultipleSelectOverlay()

    def on_mount(self) -> None:
        mutiple_select = self.query_one(MultipleSelectOverlay)
        mutiple_select.add_options(self.selections)

    def _watch_expanded(self, expanded: bool) -> None:
        """Display or hide overlay."""
        try:
            overlay = self.query_one(MultipleSelectOverlay)
        except NoMatches:
            # The widget has likely been removed
            return
        self.set_class(expanded, "-expanded")
        if expanded:
            overlay.focus(scroll_visible=False)
            if overlay._selected is None:
                self.query_one(MultipleSelectCurrent).has_value = False
            else:
                self.query_one(MultipleSelectCurrent).has_value = True

    @on(MultipleSelectCurrent.Toggle)
    def _select_current_toggle(self, event: MultipleSelectCurrent.Toggle) -> None:
        """Show the overlay when toggled."""
        event.stop()
        self.expanded = not self.expanded

    @on(MultipleSelectOverlay.Dismiss)
    def _select_overlay_dismiss(self, event: MultipleSelectOverlay.Dismiss) -> None:
        """Dismiss the overlay."""
        event.stop()
        self.expanded = False
        if not event.lost_focus:
            # If the overlay didn't lose focus, we want to re-focus the select.
            self.focus()

