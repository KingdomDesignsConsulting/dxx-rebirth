#pragma once

#include <SDL.h>

#if defined(__APPLE__)
#include <TargetConditionals.h>
#if TARGET_OS_IOS
#include <SDL_syswm.h>
#include <objc/message.h>
#include <objc/runtime.h>
#endif
#endif

namespace dcx {

struct mobile_safe_insets { float left{}, right{}, top{}, bottom{}; };

inline mobile_safe_insets mobile_get_safe_insets(SDL_Window *window)
{
#if defined(__APPLE__) && TARGET_OS_IOS
	if (!window)
		return {};
	SDL_SysWMinfo info{};
	SDL_VERSION(&info.version);
	if (!SDL_GetWindowWMInfo(window, &info) || info.subsystem != SDL_SYSWM_UIKIT || !info.info.uikit.window)
		return {};
	struct ui_edge_insets { double top, left, bottom, right; };
	auto *const native_window = reinterpret_cast<id>(info.info.uikit.window);
	auto *const selector = sel_registerName("safeAreaInsets");
	const auto get_insets = reinterpret_cast<ui_edge_insets (*)(id, SEL)>(objc_msgSend);
	const auto insets = get_insets(native_window, selector);
	return {static_cast<float>(insets.left), static_cast<float>(insets.right),
		static_cast<float>(insets.top), static_cast<float>(insets.bottom)};
#else
	(void)window;
	return {};
#endif
}

}
