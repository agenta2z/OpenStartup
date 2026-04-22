/**
 * WidgetRegistry — maps inputMode type strings to widget components.
 * Adapted from RankEvolve's WidgetRegistry.js pattern.
 *
 * Usage:
 *   import { getWidget } from './WidgetRegistry';
 *   const Widget = getWidget(widgetType);  // always returns a component (falls back to TextInputWidget)
 */

import SingleChoiceWidget from './SingleChoiceWidget';
import MultipleChoiceWidget from './MultipleChoiceWidget';
import TextInputWidget from './TextInputWidget';
import ConfirmationWidget from './ConfirmationWidget';

const WIDGET_REGISTRY = {
  // AF input_mode protocol modes
  'free_text': TextInputWidget,
  'text_input': TextInputWidget,
  'single_choice': SingleChoiceWidget,
  'multiple_choices': MultipleChoiceWidget,

  // widget_type in metadata (used by ConversationToolWidget)
  'confirmation': ConfirmationWidget,
  'press_to_continue': ConfirmationWidget,  // treated as confirmation
};

/**
 * Get the widget component for a given type string.
 * Falls back to TextInputWidget for unknown types.
 */
export function getWidget(type) {
  return WIDGET_REGISTRY[type] || WIDGET_REGISTRY['free_text'];
}

export default WIDGET_REGISTRY;
