/*
 * This file is part of the DXX-Rebirth project <https://github.com/dxx-rebirth/dxx-rebirth/>.
 * It is copyright by its individual contributors, as recorded in the
 * project's Git history.  See COPYING.txt at the top level for license
 * terms and a link to the Git history.
 */
/*
 *
 * SDL Event related stuff
 *
 *
 */

#include <ranges>
#include <cstring>
#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include "event.h"
#include "key.h"
#include "mouse.h"
#include "window.h"
#include "timer.h"
#include "cmd.h"
#include "config.h"
#include "inferno.h"
#include "gr.h"
#include "gamefont.h"

#include "joy.h"
#include "args.h"
#include "partial_range.h"
#if SDL_MAJOR_VERSION == 2
#include "mobile_touch.h"
#endif

namespace dcx {

#if SDL_MAJOR_VERSION == 2
namespace {
mobile_touch_controls touch_controls;
bool touch_gameplay_active = false;
bool touch_intro_active = false;
bool touch_intro_skipped = false;
}

void mobile_touch_set_intro_skip(bool active)
{
	touch_intro_active = active;
	if (active)
		touch_intro_skipped = false;
}

bool mobile_touch_intro_was_skipped()
{
	return touch_intro_skipped;
}

void mobile_touch_set_gameplay(bool active, bool descent2)
{
	if (!active)
		touch_controls.release_all();
	touch_controls.set_descent2(descent2);
	touch_gameplay_active = active;
}

void mobile_touch_draw_overlay(grs_canvas &canvas, SDL_Window *window)
{
	if (!window || std::strcmp(SDL_GetPlatform(), "iOS") || (!touch_gameplay_active && !touch_intro_active))
		return;
	if (const auto *front = window_get_front(); !touch_intro_active && front && front->is_touch_menu())
	{
		touch_controls.release_all();
		return;
	}
	const auto previous_fade = canvas.cv_fade_level;
	const auto previous_fg = canvas.cv_font_fg_color;
	const auto previous_bg = canvas.cv_font_bg_color;
	const auto white = gr_find_closest_color(63, 63, 63);
	if (touch_intro_active)
	{
		const float scale = std::min(canvas.cv_bitmap.bm_w / 568.f, canvas.cv_bitmap.bm_h / 320.f);
		const int left = 8 * scale;
		const int top = canvas.cv_bitmap.bm_h - 34 * scale;
		gr_settransblend(canvas, gr_fade_level{12}, gr_blend::normal);
		gr_rect(canvas, left, top, left + 96 * scale, top + 26 * scale, white);
		gr_settransblend(canvas, previous_fade, gr_blend::normal);
		gr_set_fontcolor(canvas, white, -1);
		gr_string(canvas, *GAME_FONT, left + 5 * scale, top + 7 * scale, "SKIP INTRO");
		gr_set_fontcolor(canvas, previous_fg, previous_bg);
		return;
	}
	touch_controls.for_each_button(window, [&](unsigned i, const auto &r, int width, int height, bool pressed) {
		const auto fade = static_cast<gr_fade_level>(pressed ? 8 : (i >= 13 && i <= 16 ? 28 : 24));
		gr_settransblend(canvas, fade, gr_blend::normal);
		const int left = r.x * canvas.cv_bitmap.bm_w / width;
		const int top = r.y * canvas.cv_bitmap.bm_h / height;
		const int right = (r.x + r.width) * canvas.cv_bitmap.bm_w / width;
		const int bottom = (r.y + r.height) * canvas.cv_bitmap.bm_h / height;
		gr_rect(canvas, left, top, right, bottom, white);
		gr_settransblend(canvas, previous_fade, gr_blend::normal);
		const char *const label = touch_controls.label(i);
		const int label_width = gr_get_string_size(*GAME_FONT, label).width;
		gr_set_fontcolor(canvas, white, -1);
		gr_string(canvas, *GAME_FONT, left + (right - left - label_width) / 2,
			top + (bottom - top - gr_get_string_size(*GAME_FONT, label).height) / 2, label);
	});
	gr_settransblend(canvas, previous_fade, gr_blend::normal);
	gr_set_fontcolor(canvas, previous_fg, previous_bg);
}
#endif

namespace {

struct event_poll_state
{
	uint8_t clean_uniframe{1};
	const window *const front_window = window_get_front();
	window_event_result highest_result = window_event_result::ignored;
	void process_event_batch(std::ranges::subrange<const SDL_Event *>);
};

}

#if SDL_MAJOR_VERSION == 2
extern SDL_Window *g_pRebirthSDLMainWindow;

static void windowevent_handler(const SDL_WindowEvent &windowevent)
{
	switch (windowevent.event)
	{
		case SDL_WINDOWEVENT_SIZE_CHANGED:
			{
				const d_window_size_event e{windowevent.data1, windowevent.data2};
				event_send(e);
				break;
			}
	}
}
#endif

namespace {

static void event_notify_begin_loop()
{
	const d_event_begin_loop event;
	event_send(event);
}

static void event_notify_end_loop()
{
	event_send(d_event_end_loop{});
}

}

window_event_result event_poll()
{
	event_poll_state state;
	event_notify_begin_loop();

	for (;;)
	{
	// If the front window changes, exit this loop, otherwise unintended behavior can occur
	// like pressing 'Return' really fast at 'Difficulty Level' causing multiple games to be started
		if (state.front_window != window_get_front())
			break;
		std::array<SDL_Event, 128> events;

		SDL_PumpEvents();
#if SDL_MAJOR_VERSION == 1
		const auto peep = SDL_PeepEvents(events.data(), events.size(), SDL_GETEVENT, SDL_ALLEVENTS);
#elif SDL_MAJOR_VERSION == 2
		const auto peep = SDL_PeepEvents(events.data(), events.size(), SDL_GETEVENT, SDL_FIRSTEVENT, SDL_LASTEVENT);
#endif
		if (peep <= 0)
			break;
		state.process_event_batch(unchecked_partial_range(events, static_cast<unsigned>(peep)));
		if (state.highest_result == window_event_result::deleted)
			break;
	}
	// Send the idle event if there were no other events (or they were ignored)
	if (state.highest_result == window_event_result::ignored)
	{
		const d_event ievent{event_type::idle};
		state.highest_result = std::max(event_send(ievent), state.highest_result);
	}
	else
	{
#if DXX_USE_EDITOR
		event_reset_idle_seconds();
#endif
	}
	mouse_cursor_autohide();
	event_notify_end_loop();
	return state.highest_result;
}

void event_poll_state::process_event_batch(const std::ranges::subrange<const SDL_Event *> events)
{
	for (auto &&event : events)
	{
		window_event_result result;
		switch(event.type) {
#if SDL_MAJOR_VERSION == 2
			case SDL_WINDOWEVENT:
				windowevent_handler(event.window);
				continue;
#endif
			case SDL_KEYDOWN:
			case SDL_KEYUP:
				if (clean_uniframe)
				{
					clean_uniframe=0;
					unicode_frame_buffer = {};
				}
				result = key_handler(&event.key);
				break;
			case SDL_MOUSEBUTTONDOWN:
			case SDL_MOUSEBUTTONUP:
				if (CGameArg.CtlNoMouse)
					continue;
				result = mouse_button_handler(&event.button);
				break;
			case SDL_MOUSEMOTION:
				if (CGameArg.CtlNoMouse)
					continue;
				result = mouse_motion_handler(&event.motion);
				break;
#if SDL_MAJOR_VERSION == 2
			case SDL_FINGERDOWN:
			case SDL_FINGERUP:
			case SDL_FINGERMOTION:
				if (std::strcmp(SDL_GetPlatform(), "iOS"))
					continue;
				if (touch_intro_active && event.type == SDL_FINGERDOWN)
				{
					int width = 0, height = 0;
					SDL_GL_GetDrawableSize(g_pRebirthSDLMainWindow, &width, &height);
					const float scale = std::min(width / 568.f, height / 320.f);
					const float x = event.tfinger.x * width;
					const float y = event.tfinger.y * height;
					if (x >= 8 * scale && x < 104 * scale &&
						y >= height - 34 * scale && y < height - 8 * scale)
					{
						touch_intro_skipped = true;
						SDL_KeyboardEvent escape{};
						escape.type = SDL_KEYDOWN;
						escape.state = SDL_PRESSED;
						escape.keysym.sym = SDLK_ESCAPE;
						escape.keysym.scancode = SDL_SCANCODE_ESCAPE;
						result = key_handler(&escape);
						escape.type = SDL_KEYUP;
						escape.state = SDL_RELEASED;
						key_handler(&escape);
						break;
					}
				}
				if (const auto *front = window_get_front(); front && front->is_touch_menu())
				{
					touch_controls.release_all();
					if (front->dismiss_on_outside_touch() && event.type == SDL_FINGERDOWN)
					{
						int width = 0, height = 0;
						SDL_GL_GetDrawableSize(g_pRebirthSDLMainWindow, &width, &height);
						const auto &rect = front->w_canv.cv_bitmap;
						const auto x = event.tfinger.x * width;
						const auto y = event.tfinger.y * height;
						if (x < rect.bm_x || x >= rect.bm_x + rect.bm_w ||
							y < rect.bm_y || y >= rect.bm_y + rect.bm_h)
						{
							SDL_KeyboardEvent escape{};
							escape.type = SDL_KEYDOWN;
							escape.state = SDL_PRESSED;
							escape.keysym.sym = SDLK_ESCAPE;
							escape.keysym.scancode = SDL_SCANCODE_ESCAPE;
							result = key_handler(&escape);
							escape.type = SDL_KEYUP;
							escape.state = SDL_RELEASED;
							key_handler(&escape);
							break;
						}
					}
					result = mouse_touch_handler(event.tfinger, g_pRebirthSDLMainWindow);
				}
				else if (touch_gameplay_active)
				{
					touch_controls.handle(g_pRebirthSDLMainWindow, event.tfinger);
					result = window_event_result::handled;
				}
				else
					result = mouse_touch_handler(event.tfinger, g_pRebirthSDLMainWindow);
				break;
#endif
#if DXX_MAX_JOYSTICKS
#if SDL_MAJOR_VERSION == 2
#if DXX_MAX_BUTTONS_PER_JOYSTICK
			case SDL_CONTROLLERBUTTONDOWN:
			case SDL_CONTROLLERBUTTONUP:
				if (CGameArg.CtlNoJoystick)
					continue;
				result = gc_button_handler(&event.cbutton);
				break;
#endif
#if DXX_MAX_AXES_PER_JOYSTICK
			case SDL_CONTROLLERAXISMOTION:
				if (CGameArg.CtlNoJoystick)
					continue;
#if (DXX_MAX_BUTTONS_PER_JOYSTICK || DXX_MAX_HATS_PER_JOYSTICK)
				highest_result = std::max(gc_axisbutton_handler(&event.caxis), highest_result);
#endif
				result = gc_axis_handler(&event.caxis);
				break;
#endif
			case SDL_CONTROLLERDEVICEADDED:
				result = gc_device_added(&event.cdevice);
				break;
			case SDL_CONTROLLERDEVICEREMOVED:
				result = gc_device_removed(&event.cdevice);
				break;
#endif
			case SDL_JOYBUTTONDOWN:
			case SDL_JOYBUTTONUP:
				if (CGameArg.CtlNoJoystick)
					continue;
				result = joy_button_handler(&event.jbutton);
				break;
			case SDL_JOYAXISMOTION:
				if (CGameArg.CtlNoJoystick)
					continue;
#if DXX_MAX_BUTTONS_PER_JOYSTICK || DXX_MAX_HATS_PER_JOYSTICK
				highest_result = std::max(joy_axisbutton_handler(&event.jaxis), highest_result);
#endif
				result = joy_axis_handler(&event.jaxis);
				break;
			case SDL_JOYHATMOTION:
				if (CGameArg.CtlNoJoystick)
					continue;
				result = joy_hat_handler(&event.jhat);
				break;
			case SDL_JOYBALLMOTION:
				continue;
#endif
			case SDL_QUIT: {
				result = call_default_handler(d_event{event_type::quit});
				break;
			}
			default:
				continue;
		}
		highest_result = std::max(result, highest_result);
	}
}

void event_flush()
{
	std::array<SDL_Event, 128> events;
	for (;;)
	{
		SDL_PumpEvents();
#if SDL_MAJOR_VERSION == 1
		const auto peep = SDL_PeepEvents(events.data(), events.size(), SDL_GETEVENT, SDL_ALLEVENTS);
#elif SDL_MAJOR_VERSION == 2
		const auto peep = SDL_PeepEvents(events.data(), events.size(), SDL_GETEVENT, SDL_FIRSTEVENT, SDL_LASTEVENT);
#endif
		if (peep != events.size())
			break;
	}
}

window_event_result call_default_handler(const d_event &event)
{
	return standard_handler(event);
}

window_event_result event_send(const d_event &event)
{
	window *wind;
	window_event_result handled = window_event_result::ignored;

	for (wind = window_get_front(); wind && handled == window_event_result::ignored; wind = window_get_prev(*wind))
		if (wind->is_visible())
		{
			handled = wind->send_event(event);

			if (handled == window_event_result::deleted) // break away if necessary: window_send_event() could have closed wind by now
				break;
			if (wind->is_modal())
				break;
		}
	
	if (handled == window_event_result::ignored)
		return call_default_handler(event);

	return handled;
}

// Process the first event in queue, sending to the appropriate handler
// This is the new object-oriented system
// Uses the old system for now, but this may change
window_event_result event_process(void)
{
	window *wind = window_get_front();
	window_event_result highest_result;

	timer_update();

	highest_result = event_poll();	// send input events first

	cmd_queue_process();

	// Doing this prevents problems when a draw event can create a newmenu,
	// such as some network menus when they report a problem
	// Also checking for window_event_result::deleted in case a window was created
	// with the same pointer value as the deleted one
	if ((highest_result == window_event_result::deleted) || (window_get_front() != wind))
		return highest_result;

	const d_event event{event_type::window_draw};	// then draw all visible windows
	for (wind = window_get_first(); wind != nullptr;)
	{
		if (wind->is_visible())
		{
			auto prev = window_get_prev(*wind);
			auto result = wind->send_event(event);
			highest_result = std::max(result, highest_result);
			if (result == window_event_result::deleted)
			{
				if (!prev)
				{
					wind = window_get_first();
					continue;
				}
				wind = prev;	// take the previous window and get the next one from that (if prev isn't nullptr)
			}
		}
		wind = window_get_next(*wind);
	}

	gr_flip();

	return highest_result;
}

namespace {

template <bool activate_focus>
static void event_change_focus()
{
	const auto enable_grab = activate_focus && CGameCfg.Grabinput && likely(!CGameArg.DbgForbidConsoleGrab);
#if SDL_MAJOR_VERSION == 1
	SDL_WM_GrabInput(enable_grab ? SDL_GRAB_ON : SDL_GRAB_OFF);
#elif SDL_MAJOR_VERSION == 2
	SDL_SetWindowGrab(g_pRebirthSDLMainWindow, enable_grab ? SDL_TRUE : SDL_FALSE);
	SDL_SetRelativeMouseMode(enable_grab ? SDL_TRUE : SDL_FALSE);
#endif
	if (activate_focus)
		mouse_disable_cursor();
	else
		mouse_enable_cursor();
}

}

void event_enable_focus()
{
	event_change_focus<true>();
}

void event_disable_focus()
{
	event_change_focus<false>();
}

#if DXX_USE_EDITOR
static fix64 last_event = 0;

void event_reset_idle_seconds()
{
	last_event = timer_query();
}

fix event_get_idle_seconds()
{
	return (timer_query() - last_event)/F1_0;
}
#endif

}
