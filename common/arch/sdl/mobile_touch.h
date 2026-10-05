/*
 * Touch layout adapted from Descent-Mobile and Descent2-Mobile by Devin Tuchsen.
 * See COPYING.txt for the terms of the Rebirth source tree.
 */
#pragma once

#include <SDL.h>
#include <algorithm>
#include <array>
#include <map>
#include <unordered_map>
#include "key.h"
#include "mobile_safe_area.h"

namespace dcx {

/* SDL finger positions are normalized to the window.  Keep the original
 * 568x320 layout, scaling uniformly so buttons remain usable on iPad. */
class mobile_touch_controls
{
	struct button
	{
		float x, y, width, height;
		SDL_Keycode primary, secondary;
		bool follow_finger;
	};
	struct rectangle
	{
		float x, y, width, height;
	};

	// Rotation, translation and thrust use separate buttons in manual mode.
	// Gyro mode reuses the center and left buttons for translation and thrust.
	static constexpr std::array<button, 27> buttons{{
		{120, 135, 55, 55, SDLK_UP, 0, true},
		{120, 245, 55, 55, SDLK_DOWN, 0, true},
		{65, 190, 55, 55, SDLK_q, 0, true},
		{175, 190, 55, 55, SDLK_e, 0, true},
		{25, 135, 35, 80, SDLK_KP_MINUS, 0, true},
		{25, 220, 35, 80, SDLK_KP_PLUS, 0, true},
		{65, 95, 0, 0, 0, 0, true},
		{150, 95, 0, 0, 0, 0, true},
		{473, 150, 70, 70, SDLK_LCTRL, 0, false},
		{393, 230, 70, 70, SDLK_SPACE, 0, false},
		{473, 95, 70, 40, SDLK_1, 0, false},
		{338, 230, 40, 70, SDLK_6, 0, false},
		{483, 240, 50, 50, SDLK_f, 0, false},
		{65, 135, 55, 55, SDLK_LEFT, 0, true},
		{175, 135, 55, 55, SDLK_RIGHT, 0, true},
		{65, 245, 55, 55, SDLK_KP_1, 0, true},
		{175, 245, 55, 55, SDLK_KP_3, 0, true},
		{25, 20, 25, 25, SDLK_ESCAPE, 0, false},
		{0, 20, 25, 25, SDLK_TAB, 0, false},
		{0, 20, 25, 25, SDLK_r, 0, false},
		{0, 20, 25, 25, SDLK_F3, 0, false},
		{0, 20, 25, 25, SDLK_h, 0, false},
		{0, 20, 25, 25, SDLK_t, 0, false},
		{0, 20, 25, 25, SDLK_F4, 0, false},
		{0, 20, 25, 25, SDLK_LSHIFT, SDLK_F4, false},
		{120, 190, 55, 55, SDLK_w, 0, true},
		{230, 245, 55, 55, SDLK_s, 0, true},
	}};

	std::unordered_map<SDL_FingerID, unsigned> fingers;
	std::map<SDL_Keycode, unsigned> held_keys;
	bool descent2 = false;
	bool gyro_mode = false;
	static constexpr std::array<const char *, 27> labels{{
		"UP", "DOWN", "TW L", "TW R", "SL U", "SL D", "", "",
		"FIRE", "MISSILE", "WPN 1", "WPN 6", "FLARE",
		"LEFT", "RIGHT", "SL L", "SL R",
		"MENU", "MAP", "R", "F3", "H", "T", "F4", "GB", "FWD", "BACK"
	}};
	static constexpr std::array<const char *, 27> gyro_labels{{
		"SL U", "SL D", "", "", "FWD", "BACK", "", "",
		"FIRE", "MISSILE", "WPN 1", "WPN 6", "FLARE",
		"", "", "SL L", "SL R",
		"MENU", "MAP", "R", "F3", "H", "T", "F4", "GB", "", ""
	}};

	button active_button(unsigned i) const
	{
		auto b = buttons[i];
		if (gyro_mode)
		{
			if (i == 0) b.primary = SDLK_KP_MINUS;
			if (i == 1) b.primary = SDLK_KP_PLUS;
			if (i == 4) b.primary = SDLK_w;
			if (i == 5) b.primary = SDLK_s;
			if (i == 2 || i == 3 || i == 13 || i == 14 || i == 25 || i == 26)
				b.width = b.height = 0;
		}
		return b;
	}

	static SDL_KeyboardEvent keyboard_event(SDL_Keycode key, bool down)
	{
		SDL_KeyboardEvent event{};
		event.type = down ? SDL_KEYDOWN : SDL_KEYUP;
		event.state = down ? SDL_PRESSED : SDL_RELEASED;
		event.keysym.sym = key;
		event.keysym.scancode = SDL_GetScancodeFromKey(key);
		return event;
	}

	static bool has_key(const button &b, SDL_Keycode key)
	{
		return b.primary == key || b.secondary == key;
	}

	void set_key(SDL_Keycode key, bool down)
	{
		if (!key)
			return;
		auto &count = held_keys[key];
		if (down)
		{
			if (count++ == 0)
			{
				auto event = keyboard_event(key, true);
				key_handler(&event);
			}
		}
		else if (count && --count == 0)
		{
			auto event = keyboard_event(key, false);
			key_handler(&event);
		}
	}

	void transition(unsigned old_button, unsigned new_button)
	{
		const button empty{};
		const auto old = old_button < buttons.size() ? active_button(old_button) : empty;
		const auto next = new_button < buttons.size() ? active_button(new_button) : empty;
		for (const auto key : {old.primary, old.secondary})
			if (key && !has_key(next, key))
				set_key(key, false);
		for (const auto key : {next.primary, next.secondary})
			if (key && !has_key(old, key))
				set_key(key, true);
	}

	rectangle geometry(unsigned i, int width, int height, const mobile_safe_insets safe) const
	{
		const float scale = std::min(width / 568.f, height / 320.f);
		const auto &b = buttons[i];
		float left = (i >= 8 && i <= 12) ? width - (568 - b.x) * scale : b.x * scale;
		float top = height - (320 - b.y) * scale;
		if (i < 8 || (i >= 13 && i <= 16) || i >= 25)
			left += std::max(0.f, safe.left + 8.f - 25.f * scale);
		else if (i >= 8 && i <= 12)
			left -= std::max(0.f, safe.right + 8.f - 25.f * scale);
		if (i >= 17)
		{
			const unsigned position = i == 17 ? 0 : i == 20 ? 1 : i == 19 ? 2 :
				i == 21 ? 3 : i == 22 ? 4 : i == 23 ? 5 : i == 24 ? 6 : descent2 ? 7 : 3;
			if (i <= 24)
				left = safe.left + 8 * scale + position * (width - safe.left - safe.right - 58 * scale) / (descent2 ? 7 : 3);
			top = 20 * scale;
		}
		if (i >= 25)
			top = height - (320 - b.y) * scale;
		return {left, top, b.width * scale, b.height * scale};
	}

	unsigned hit_test(SDL_Window *window, float normalized_x, float normalized_y) const
	{
		int width = 0, height = 0;
		if (window)
			SDL_GetWindowSize(window, &width, &height);
		if (width <= 0 || height <= 0)
			return buttons.size();
		const float x = normalized_x * width, y = normalized_y * height;
		const auto safe = mobile_get_safe_insets(window);
		for (unsigned i = 0; i != buttons.size(); ++i)
		{
			if (!descent2 && i >= 21 && i <= 24)
				continue;
			const auto b = active_button(i);
			const auto r = geometry(i, width, height, safe);
			if (!b.width || !b.height)
				continue;
			if (x >= r.x && x < r.x + r.width && y >= r.y && y < r.y + r.height)
				return i;
		}
		return buttons.size();
	}

public:
	template <typename Callback>
	void for_each_button(SDL_Window *window, Callback callback) const
	{
		int width = 0, height = 0;
		if (window)
			SDL_GetWindowSize(window, &width, &height);
		if (width <= 0 || height <= 0)
			return;
		const auto safe = mobile_get_safe_insets(window);
		for (unsigned i = 0; i != buttons.size(); ++i)
		{
			if ((!descent2 && i >= 21 && i <= 24) || !active_button(i).width)
				continue;
			bool pressed = false;
			for (const auto &[finger, index] : fingers)
			{
				(void)finger;
				if (index == i)
					pressed = true;
			}
			callback(i, geometry(i, width, height, safe), width, height, pressed);
		}
	}
	const char *label(unsigned i) const { return (gyro_mode ? gyro_labels : labels)[i]; }
	void set_gyro_mode(bool value)
	{
		if (gyro_mode != value)
			release_all();
		gyro_mode = value;
	}
	void set_descent2(bool value)
	{
		if (descent2 != value)
			release_all();
		descent2 = value;
	}

	void release_all()
	{
		for (const auto &[finger, index] : fingers)
		{
			(void)finger;
			transition(index, buttons.size());
		}
		fingers.clear();
	}

	void handle(SDL_Window *window, const SDL_TouchFingerEvent &event)
	{
		const auto hit = hit_test(window, event.x, event.y);
		auto current = fingers.find(event.fingerId);
		if (event.type == SDL_FINGERUP)
		{
			if (current != fingers.end())
			{
				transition(current->second, buttons.size());
				fingers.erase(current);
			}
			return;
		}
		if (event.type == SDL_FINGERDOWN)
		{
			if (hit != buttons.size())
			{
				fingers[event.fingerId] = hit;
				transition(buttons.size(), hit);
			}
			return;
		}
		if (current != fingers.end() && current->second != hit &&
			buttons[current->second].follow_finger)
		{
			transition(current->second, hit);
			if (hit == buttons.size())
				fingers.erase(current);
			else
				current->second = hit;
		}
	}
};

}
