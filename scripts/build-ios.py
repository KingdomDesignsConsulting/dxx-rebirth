#!/usr/bin/env python3
"""Build D1X and D2X Apple mobile app bundles from the shared Rebirth source tree.

Requires Xcode, CMake, SCons, pkg-config, and the user's licensed game data.
The pinned third-party sources and compiled dependencies stay in a cache
outside this repository. No licensed assets are added to Git.
"""

import argparse
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tarfile
import urllib.request


ROOT = Path(__file__).resolve().parent.parent
SDL_PATCH_REVISION = "2026-10-06-uiscene-v1"
VERSIONS = {
    "SDL2": ("2.32.10", "https://github.com/libsdl-org/SDL/releases/download/release-2.32.10/SDL2-2.32.10.tar.gz"),
    "SDL2_image": ("2.8.12", "https://github.com/libsdl-org/SDL_image/releases/download/release-2.8.12/SDL2_image-2.8.12.tar.gz"),
    "SDL2_mixer": ("2.8.1", "https://github.com/libsdl-org/SDL_mixer/releases/download/release-2.8.1/SDL2_mixer-2.8.1.tar.gz"),
    "physfs": ("3.2.0", "https://github.com/icculus/physfs/archive/refs/tags/release-3.2.0.tar.gz"),
}
SHA256 = {
    "SDL2": "5f5993c530f084535c65a6879e9b26ad441169b3e25d789d83287040a9ca5165",
    "SDL2_image": "393f5efb50536ec13ca4f4affb69cc9966d3c3f969e6c5e701faddf9f9785381",
    "SDL2_mixer": "cb760211b056bfe44f4a1e180cc7cb201137e4d1572f2002cc1be728efd22660",
    "physfs": "1991500eaeb8d5325e3a8361847ff3bf8e03ec89252b7915e1f25b3f8ab5d560",
}


def run(*args, env=None):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=ROOT, env=env, check=True)


def source(cache, name, variant=None):
    version, url = VERSIONS[name]
    dirname = f"physfs-release-{version}" if name == "physfs" else f"{name}-{version}"
    src = cache / (f"{dirname}-{variant}" if variant else dirname)
    marker = src / ".dxx-source-sha256"
    archive = cache / f"{name}-{version}.tar.gz"

    def ensure_archive():
        if not archive.exists():
            print(f"Downloading {name} {version}", flush=True)
            urllib.request.urlretrieve(url, archive)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != SHA256[name]:
            raise RuntimeError(f"Checksum mismatch for {archive}: {digest}")

    # A pre-existing extracted directory is not authoritative by itself.  It
    # must carry the identity of the pinned archive it came from.  Older caches
    # without a marker are discarded once and recreated from the verified
    # archive.  Target-specific SDL trees also carry a patch revision so a
    # changed UIKit/tvOS backport cannot silently reuse stale patched source.
    if src.exists():
        marker_ok = marker.is_file() and marker.read_text().strip() == SHA256[name]
        patch_ok = True
        if name == "SDL2" and variant:
            patch_marker = src / ".dxx-patch-revision"
            patch_ok = (patch_marker.is_file() and
                        patch_marker.read_text().strip() == SDL_PATCH_REVISION)
        if marker_ok and patch_ok:
            return src
        print(f"Refreshing stale/unverified cached source: {src}", flush=True)
        shutil.rmtree(src)

    ensure_archive()

    # SDL is patched per Apple target/platform.  Keep target-specific source
    # trees instead of mutating a shared verified extraction.
    if variant:
        staging = cache / f".{dirname}-{variant}-extract"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir()
        with tarfile.open(archive) as tf:
            for member in tf.getmembers():
                target = (staging / member.name).resolve()
                if not target.is_relative_to(staging.resolve()):
                    raise RuntimeError(f"Unsafe archive path: {member.name}")
            tf.extractall(staging)
        extracted = staging / dirname
        if not extracted.exists():
            raise RuntimeError(f"Missing extracted source: {extracted}")
        extracted.rename(src)
        staging.rmdir()
        marker.write_text(SHA256[name] + "\n")
        return src

    with tarfile.open(archive) as tf:
        for member in tf.getmembers():
            target = (cache / member.name).resolve()
            if not target.is_relative_to(cache.resolve()):
                raise RuntimeError(f"Unsafe archive path: {member.name}")
        tf.extractall(cache)
    if not src.exists():
        raise RuntimeError(f"Missing extracted source: {src}")
    marker.write_text(SHA256[name] + "\n")
    return src



def patch_sdl_apple_scene_lifecycle(sdl, target_os):
    """Backport maintained SDL UIKit scene/orientation handling to pinned SDL2."""
    appdelegate_h = sdl / "src/video/uikit/SDL_uikitappdelegate.h"
    header_text = appdelegate_h.read_text()
    header_marker = "/* DXX Apple UIScene lifecycle backport */"
    if header_marker not in header_text:
        needle = "@interface SDLUIKitDelegate : NSObject<UIApplicationDelegate>\n"
        scene_decl = (
            header_marker + "\n"
            "API_AVAILABLE(ios(13.0), tvos(13.0))\n"
            "@interface SDLUIKitSceneDelegate : NSObject <UIApplicationDelegate, UIWindowSceneDelegate>\n"
            "+ (NSString *)getSceneDelegateClassName;\n"
            "- (void)hideLaunchScreen;\n"
            "@end\n\n"
        )
        if needle not in header_text:
            raise RuntimeError(f"Could not add SDL UIKit scene delegate declaration in {appdelegate_h}")
        appdelegate_h.write_text(header_text.replace(needle, scene_decl + needle, 1))

    appdelegate = sdl / "src/video/uikit/SDL_uikitappdelegate.m"
    text = appdelegate.read_text()
    old_stub = """/* DXX tvOS UIScene compatibility shim */
#if TARGET_OS_TV
@interface SDLUIKitSceneDelegate : UIResponder <UIWindowSceneDelegate>
@end
@implementation SDLUIKitSceneDelegate
@end
#endif

"""
    if old_stub in text:
        text = text.replace(old_stub, "", 1)

    run_marker = "/* DXX Apple UIScene UIApplicationMain backport */"
    if run_marker not in text:
        old_run = "        UIApplicationMain(argc, argv, nil, [SDLUIKitDelegate getAppDelegateClassName]);\n"
        new_run = """        /* DXX Apple UIScene UIApplicationMain backport */
        NSString *delegateClassName = [SDLUIKitDelegate getAppDelegateClassName];
        if (@available(iOS 13.0, tvOS 13.0, *)) {
            delegateClassName = [SDLUIKitSceneDelegate getSceneDelegateClassName];
        }
        UIApplicationMain(argc, argv, nil, delegateClassName);
"""
        if old_run not in text:
            raise RuntimeError(f"Could not patch UIApplicationMain scene delegate selection in {appdelegate}")
        text = text.replace(old_run, new_run, 1)

    text = text.replace("[UIApplication sharedApplication].statusBarOrientation", "UIKit_GetInterfaceOrientation()")

    scene_marker = "/* DXX Apple UIScene lifecycle implementation */"
    if scene_marker not in text:
        needle = "@implementation SDLUIKitDelegate {\n"
        scene_impl = '''/* DXX Apple UIScene lifecycle implementation */
API_AVAILABLE(ios(13.0), tvos(13.0))
@implementation SDLUIKitSceneDelegate {
    UIWindow *launchWindow;
}

+ (NSString *)getSceneDelegateClassName
{
    return @"SDLUIKitSceneDelegate";
}

- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session options:(UISceneConnectionOptions *)connectionOptions
{
    if (![scene isKindOfClass:[UIWindowScene class]]) {
        return;
    }
    UIWindowScene *windowScene = (UIWindowScene *)scene;
    windowScene.delegate = self;
    NSBundle *bundle = [NSBundle mainBundle];
#ifdef SDL_IPHONE_LAUNCHSCREEN
    UIViewController *vc = nil;
    NSString *screenname = nil;
#if !TARGET_OS_TV
    screenname = [bundle objectForInfoDictionaryKey:@"UILaunchStoryboardName"];
    if (screenname) {
        @try {
            UIStoryboard *storyboard = [UIStoryboard storyboardWithName:screenname bundle:bundle];
            __auto_type storyboardVc = [storyboard instantiateInitialViewController];
            vc = [[SDLLaunchStoryboardViewController alloc] initWithStoryboardViewController:storyboardVc];
        }
        @catch (NSException *exception) {
        }
    }
#endif
    if (vc == nil) {
        vc = [[SDLLaunchScreenController alloc] initWithNibName:screenname bundle:bundle];
    }
    if (vc.view) {
        launchWindow = [[UIWindow alloc] initWithWindowScene:windowScene];
        launchWindow.frame = windowScene.coordinateSpace.bounds;
        launchWindow.windowLevel = UIWindowLevelNormal + 1.0;
        launchWindow.hidden = NO;
        launchWindow.rootViewController = vc;
    }
#endif
    [[NSFileManager defaultManager] changeCurrentDirectoryPath:[bundle resourcePath]];
    SDL_AddHintCallback(SDL_HINT_IDLE_TIMER_DISABLED, SDL_IdleTimerDisabledChanged, NULL);
    SDL_SetMainReady();
    [self performSelector:@selector(postFinishLaunch) withObject:nil afterDelay:0.0];
    for (UIOpenURLContext *context in connectionOptions.URLContexts) {
        [self handleURL:context.URL];
    }
}

#if !TARGET_OS_TV && __IPHONE_OS_VERSION_MAX_ALLOWED >= 270000
- (void)windowScene:(UIWindowScene *)windowScene didUpdateEffectiveGeometry:(UIWindowSceneGeometry *)previousEffectiveGeometry API_AVAILABLE(ios(26.0))
{
    if (@available(iOS 27.0, *)) {
        if (windowScene.effectiveGeometry.interfaceOrientation != previousEffectiveGeometry.interfaceOrientation) {
            SDL_OnApplicationDidChangeStatusBarOrientation();
        }
    }
}
#endif

- (void)sceneDidBecomeActive:(UIScene *)scene { SDL_OnApplicationDidBecomeActive(); }
- (void)sceneWillResignActive:(UIScene *)scene { SDL_OnApplicationWillResignActive(); }
- (void)sceneWillEnterForeground:(UIScene *)scene { SDL_OnApplicationWillEnterForeground(); }
- (void)sceneDidEnterBackground:(UIScene *)scene { SDL_OnApplicationDidEnterBackground(); }
- (void)applicationWillTerminate:(UIApplication *)application { SDL_OnApplicationWillTerminate(); }
- (void)applicationDidReceiveMemoryWarning:(UIApplication *)application { SDL_OnApplicationDidReceiveMemoryWarning(); }

- (void)scene:(UIScene *)scene openURLContexts:(NSSet<UIOpenURLContext *> *)URLContexts
{
    for (UIOpenURLContext *context in URLContexts) {
        [self handleURL:context.URL];
    }
}

- (void)handleURL:(NSURL *)url
{
    NSURL *fileURL = url.filePathURL;
    if (fileURL != nil) {
        SDL_SendDropFile(NULL, fileURL.path.UTF8String);
    } else {
        SDL_SendDropFile(NULL, url.absoluteString.UTF8String);
    }
    SDL_SendDropComplete(NULL);
}

- (void)hideLaunchScreen
{
    UIWindow *window = launchWindow;
    if (!window || window.hidden) {
        return;
    }
    launchWindow = nil;
    [UIView animateWithDuration:0.2 animations:^{ window.alpha = 0.0; }
                     completion:^(BOOL finished) {
        window.hidden = YES;
        UIKit_ForceUpdateHomeIndicator();
    }];
}

- (void)postFinishLaunch
{
    [self performSelector:@selector(hideLaunchScreen) withObject:nil afterDelay:0.0];
    SDL_iPhoneSetEventPump(SDL_TRUE);
    exit_status = forward_main(forward_argc, forward_argv);
    SDL_iPhoneSetEventPump(SDL_FALSE);
    if (launchWindow) {
        launchWindow.hidden = YES;
        launchWindow = nil;
    }
}

- (UISceneConfiguration *)application:(UIApplication *)application configurationForConnectingSceneSession:(UISceneSession *)connectingSceneSession options:(UISceneConnectionOptions *)options
{
    UISceneConfiguration *config = [[UISceneConfiguration alloc] initWithName:@"SDLSceneConfiguration" sessionRole:connectingSceneSession.role];
    config.delegateClass = [SDLUIKitSceneDelegate class];
    return config;
}

@end

'''
        if needle not in text:
            raise RuntimeError(f"Could not insert SDL UIKit scene implementation in {appdelegate}")
        text = text.replace(needle, scene_impl + needle, 1)
    appdelegate.write_text(text)

    video_h = sdl / "src/video/uikit/SDL_uikitvideo.h"
    vh = video_h.read_text()
    video_h_marker = "/* DXX Apple active UIWindowScene helpers */"
    if video_h_marker not in vh:
        needle = "CGRect UIKit_ComputeViewFrame(SDL_Window *window, UIScreen *screen);\n"
        addition = needle + "\n" + video_h_marker + "\nUIWindowScene *UIKit_GetActiveWindowScene(void);\n#if !TARGET_OS_TV\nUIInterfaceOrientation UIKit_GetInterfaceOrientation(void);\n#endif\n"
        if needle not in vh:
            raise RuntimeError(f"Could not add UIWindowScene helpers to {video_h}")
        video_h.write_text(vh.replace(needle, addition, 1))

    video_m = sdl / "src/video/uikit/SDL_uikitvideo.m"
    vm = video_m.read_text().replace("orient = [UIApplication sharedApplication].statusBarOrientation;", "orient = UIKit_GetInterfaceOrientation();")
    video_marker = "/* DXX Apple active UIWindowScene implementation */"
    if video_marker not in vm:
        needle = "/*\n * iOS log support.\n"
        helpers = '''/* DXX Apple active UIWindowScene implementation */
UIWindowScene *UIKit_GetActiveWindowScene(void)
{
    if (@available(iOS 13.0, tvOS 13.0, *)) {
        NSSet<UIScene *> *connectedScenes = [UIApplication sharedApplication].connectedScenes;
        for (UIScene *scene in connectedScenes) {
            if ([scene isKindOfClass:[UIWindowScene class]] && scene.activationState == UISceneActivationStateForegroundActive) {
                return (UIWindowScene *)scene;
            }
        }
        for (UIScene *scene in connectedScenes) {
            if ([scene isKindOfClass:[UIWindowScene class]] && scene.activationState == UISceneActivationStateForegroundInactive) {
                return (UIWindowScene *)scene;
            }
        }
        for (UIScene *scene in connectedScenes) {
            if ([scene isKindOfClass:[UIWindowScene class]]) {
                return (UIWindowScene *)scene;
            }
        }
    }
    return nil;
}

#if !TARGET_OS_TV
UIInterfaceOrientation UIKit_GetInterfaceOrientation(void)
{
#if __IPHONE_OS_VERSION_MAX_ALLOWED >= 270000
    if (@available(iOS 27.0, *)) {
        UIWindowScene *windowScene = UIKit_GetActiveWindowScene();
        if (windowScene != nil) {
            return windowScene.effectiveGeometry.interfaceOrientation;
        }
        return UIInterfaceOrientationUnknown;
    }
#endif
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    return [UIApplication sharedApplication].statusBarOrientation;
#pragma clang diagnostic pop
}
#endif

'''
        if needle not in vm:
            raise RuntimeError(f"Could not insert UIWindowScene helpers in {video_m}")
        vm = vm.replace(needle, helpers + needle, 1)
    video_m.write_text(vm)

    modes = sdl / "src/video/uikit/SDL_uikitmodes.m"
    modes.write_text(modes.read_text().replace("[UIApplication sharedApplication].statusBarOrientation", "UIKit_GetInterfaceOrientation()"))

    events = sdl / "src/video/uikit/SDL_uikitevents.m"
    events_text = events.read_text()
    events_marker = "/* DXX Apple UIScene notification de-duplication */"
    if events_marker not in events_text:
        old = """    if (UIKit_EventPumpEnabled && !self.isObservingNotifications) {
        self.isObservingNotifications = YES;
        [notificationCenter addObserver:self selector:@selector(applicationDidBecomeActive) name:UIApplicationDidBecomeActiveNotification object:nil];
        [notificationCenter addObserver:self selector:@selector(applicationWillResignActive) name:UIApplicationWillResignActiveNotification object:nil];
        [notificationCenter addObserver:self selector:@selector(applicationDidEnterBackground) name:UIApplicationDidEnterBackgroundNotification object:nil];
        [notificationCenter addObserver:self selector:@selector(applicationWillEnterForeground) name:UIApplicationWillEnterForegroundNotification object:nil];
        [notificationCenter addObserver:self selector:@selector(applicationWillTerminate) name:UIApplicationWillTerminateNotification object:nil];
        [notificationCenter addObserver:self selector:@selector(applicationDidReceiveMemoryWarning) name:UIApplicationDidReceiveMemoryWarningNotification object:nil];
#if !TARGET_OS_TV
        [notificationCenter addObserver:self selector:@selector(applicationDidChangeStatusBarOrientation) name:UIApplicationDidChangeStatusBarOrientationNotification object:nil];
#endif
"""
        new = """    if (UIKit_EventPumpEnabled && !self.isObservingNotifications) {
        self.isObservingNotifications = YES;
        /* DXX Apple UIScene notification de-duplication */
        BOOL usesSceneLifecycle = NO;
        if (@available(iOS 13.0, tvOS 13.0, *)) {
            usesSceneLifecycle = ([[NSBundle mainBundle] objectForInfoDictionaryKey:@"UIApplicationSceneManifest"] != nil);
        }
        if (!usesSceneLifecycle) {
            [notificationCenter addObserver:self selector:@selector(applicationDidBecomeActive) name:UIApplicationDidBecomeActiveNotification object:nil];
            [notificationCenter addObserver:self selector:@selector(applicationWillResignActive) name:UIApplicationWillResignActiveNotification object:nil];
            [notificationCenter addObserver:self selector:@selector(applicationDidEnterBackground) name:UIApplicationDidEnterBackgroundNotification object:nil];
            [notificationCenter addObserver:self selector:@selector(applicationWillEnterForeground) name:UIApplicationWillEnterForegroundNotification object:nil];
            [notificationCenter addObserver:self selector:@selector(applicationWillTerminate) name:UIApplicationWillTerminateNotification object:nil];
            [notificationCenter addObserver:self selector:@selector(applicationDidReceiveMemoryWarning) name:UIApplicationDidReceiveMemoryWarningNotification object:nil];
#if !TARGET_OS_TV
            [notificationCenter addObserver:self selector:@selector(applicationDidChangeStatusBarOrientation) name:UIApplicationDidChangeStatusBarOrientationNotification object:nil];
#endif
        }
"""
        if old not in events_text:
            raise RuntimeError(f"Could not patch SDL UIKit lifecycle notification observers in {events}")
        events.write_text(events_text.replace(old, new, 1))

    uikitwindow = sdl / "src/video/uikit/SDL_uikitwindow.m"
    window_text = uikitwindow.read_text().replace("/* DXX tvOS UIWindowScene attachment shim */", "/* DXX Apple UIWindowScene attachment backport */")
    marker = "/* DXX Apple UIWindowScene attachment backport */"
    if marker not in window_text:
        old_decl = "        UIWindow *uiwindow;\n"
        if old_decl not in window_text:
            raise RuntimeError(f"Could not find UIKit window declaration in {uikitwindow}")
        window_text = window_text.replace(old_decl, "        UIWindow *uiwindow = nil;\n", 1)
        old_create = """        /* ignore the size user requested, and make a fullscreen window */
        /* !!! FIXME: can we have a smaller view? */
        uiwindow = [[SDL_uikitwindow alloc] initWithFrame:data.uiscreen.bounds];
"""
        new_create = """        /* DXX Apple UIWindowScene attachment backport */
        if (@available(iOS 13.0, tvOS 13.0, *)) {
            UIWindowScene *windowScene = UIKit_GetActiveWindowScene();
            if (windowScene != nil) {
                uiwindow = [[SDL_uikitwindow alloc] initWithWindowScene:windowScene];
            }
        }
        /* ignore the size user requested, and make a fullscreen window */
        /* !!! FIXME: can we have a smaller view? */
        if (!uiwindow) {
            uiwindow = [[SDL_uikitwindow alloc] initWithFrame:data.uiscreen.bounds];
        }
"""
        if old_create not in window_text:
            raise RuntimeError(f"Could not patch UIWindowScene attachment in {uikitwindow}")
        window_text = window_text.replace(old_create, new_create, 1)
    else:
        old_body = """/* DXX Apple UIWindowScene attachment backport */
#if TARGET_OS_TV
        if (@available(tvOS 13.0, *)) {
            for (UIScene *scene in [UIApplication sharedApplication].connectedScenes) {
                if ([scene isKindOfClass:[UIWindowScene class]]) {
                    uiwindow = [[SDL_uikitwindow alloc] initWithWindowScene:(UIWindowScene *)scene];
                    break;
                }
            }
        }
#endif"""
        new_body = """/* DXX Apple UIWindowScene attachment backport */
        if (@available(iOS 13.0, tvOS 13.0, *)) {
            UIWindowScene *windowScene = UIKit_GetActiveWindowScene();
            if (windowScene != nil) {
                uiwindow = [[SDL_uikitwindow alloc] initWithWindowScene:windowScene];
            }
        }"""
        if old_body in window_text:
            window_text = window_text.replace(old_body, new_body, 1)
    uikitwindow.write_text(window_text)

    uikitview = sdl / "src/video/uikit/SDL_uikitview.m"
    view_text = uikitview.read_text()
    obsolete_marker = "/* DXX tvOS root view-controller transition shim */"
    if obsolete_marker in view_text:
        obsolete_reset = """        /* DXX tvOS root view-controller transition shim */
#if TARGET_OS_TV
        if (data.uiwindow.rootViewController != data.viewcontroller)
            data.uiwindow.rootViewController = data.viewcontroller;
#else
        data.uiwindow.rootViewController = nil;
        data.uiwindow.rootViewController = data.viewcontroller;
#endif
"""
        original_reset = """        data.uiwindow.rootViewController = nil;
        data.uiwindow.rootViewController = data.viewcontroller;
"""
        count = view_text.count(obsolete_reset)
        if count != 2:
            raise RuntimeError(f"Could not safely remove obsolete tvOS root view-controller shim in {uikitview}: found {count} blocks")
        uikitview.write_text(view_text.replace(obsolete_reset, original_reset))

    # Record which DXX patch set produced this target-specific SDL tree.
    # source() uses this to invalidate stale cached patches on later builds.
    (sdl / ".dxx-patch-revision").write_text(SDL_PATCH_REVISION + "\n")

    if target_os != "tvos":
        return

    viewcontroller = sdl / "src/video/uikit/SDL_uikitviewcontroller.m"
    controller_text = viewcontroller.read_text()
    obsolete_markers = (
        "/* DXX tvOS keyboard avoidance shim */",
        "/* DXX tvOS keyboard layout-guide shim */",
        "/* DXX tvOS keyboard safe-region shim */",
        "/* DXX tvOS text prompt shim */",
    )
    if any(marker in controller_text for marker in obsolete_markers):
        archive = sdl.parent / f"SDL2-{VERSIONS['SDL2'][0]}.tar.gz"
        if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256["SDL2"]:
            raise RuntimeError(f"Checksum mismatch for {archive}")
        member_name = f"SDL2-{VERSIONS['SDL2'][0]}/src/video/uikit/SDL_uikitviewcontroller.m"
        with tarfile.open(archive) as tf:
            member = tf.getmember(member_name)
            pristine = tf.extractfile(member)
            if pristine is None:
                raise RuntimeError(f"Could not restore pristine SDL UIKit view controller from {archive}")
            viewcontroller.write_bytes(pristine.read())
        controller_text = viewcontroller.read_text()

    prompt_marker = "/* DXX tvOS text prompt and editing shim */"
    if prompt_marker not in controller_text:
        old = """    keyboardVisible = YES;
    if (textField.window) {
        showingKeyboard = YES;
        [textField becomeFirstResponder];
    }
"""
        new = """    keyboardVisible = YES;
#if TARGET_OS_TV
    /* DXX tvOS text prompt and editing shim */
    const char *prompt = SDL_GetHint("DXX_TVOS_TEXT_PROMPT");
    textField.placeholder = prompt ? [NSString stringWithUTF8String:prompt] : nil;
    textField.accessibilityLabel = textField.placeholder;
    textField.text = @"";
    committedText = textField.text;
#endif
    if (textField.window) {
        showingKeyboard = YES;
        [textField becomeFirstResponder];
    }
"""
        if old not in controller_text:
            raise RuntimeError(f"Could not patch tvOS text prompt in {viewcontroller}")
        controller_text = controller_text.replace(old, new, 1)
        edit_old = """    if (textField.markedTextRange == nil) {
        if (textField.text.length < 16) {
            textField.text = obligateForBackspace;
            committedText = textField.text;
        }
    }
"""
        edit_new = """#if !TARGET_OS_TV
    if (textField.markedTextRange == nil) {
        if (textField.text.length < 16) {
            textField.text = obligateForBackspace;
            committedText = textField.text;
        }
    }
#endif
"""
        if edit_old not in controller_text:
            raise RuntimeError(f"Could not patch tvOS text editing in {viewcontroller}")
        viewcontroller.write_text(controller_text.replace(edit_old, edit_new, 1))

    (sdl / ".dxx-patch-revision").write_text(SDL_PATCH_REVISION + "\n")

def configure_and_build(src, out, *options):
    run("cmake", "-S", src, "-B", out, *options)
    run("cmake", "--build", out, "--parallel", "4")


def write_pc(path, name, version, include, library_dir, libs):
    path.write_text(
        f"Name: {name}\nDescription: Apple mobile static {name}\nVersion: {version}\n"
        f"Cflags: -I{include}\nLibs: -L{library_dir} {libs}\n"
    )


def build_dependencies(cache, target_os, platform):
    if target_os == "ios":
        suffix = platform
        sdk = "iphonesimulator" if platform == "simulator" else "iphoneos"
        cmake_system = "iOS"
    else:
        suffix = f"tvos-{platform}"
        sdk = "appletvsimulator" if platform == "simulator" else "appletvos"
        cmake_system = "tvOS"
    common = (
        f"-DCMAKE_SYSTEM_NAME={cmake_system}", f"-DCMAKE_OSX_SYSROOT={sdk}",
        "-DCMAKE_OSX_ARCHITECTURES=arm64", "-DCMAKE_OSX_DEPLOYMENT_TARGET=15.0",
    )
    sdl = source(cache, "SDL2", f"{target_os}-{platform}")
    patch_sdl_apple_scene_lifecycle(sdl, target_os)
    physfs = source(cache, "physfs")
    image = source(cache, "SDL2_image")
    mixer = source(cache, "SDL2_mixer")
    sdl_out = cache / f"sdl2-{suffix}"
    physfs_out = cache / f"physfs-{suffix}"
    image_out = cache / f"image-{suffix}"
    mixer_out = cache / f"mixer-{suffix}"
    configure_and_build(sdl, sdl_out, *common, "-DSDL_STATIC=ON", "-DSDL_SHARED=OFF", "-DSDL_TEST=OFF")
    configure_and_build(physfs, physfs_out, *common,
                        "-DCMAKE_POLICY_VERSION_MINIMUM=3.5", "-DPHYSFS_BUILD_STATIC=ON",
                        "-DPHYSFS_BUILD_SHARED=OFF", "-DPHYSFS_BUILD_TEST=OFF", "-DPHYSFS_BUILD_DOCS=OFF")
    sdl_lib = f"-DSDL2_LIBRARY={sdl_out / 'libSDL2.a'}"
    sdl_headers = f"-DSDL2_INCLUDE_DIR={sdl / 'include'}"
    no_host_sdl = "-DSDL2_DIR=SDL2_DIR-NOTFOUND"
    configure_and_build(image, image_out, *common, sdl_lib, sdl_headers, no_host_sdl,
                        "-DBUILD_SHARED_LIBS=OFF", "-DSDL2IMAGE_SAMPLES=OFF",
                        "-DSDL2IMAGE_AVIF=OFF", "-DSDL2IMAGE_TIF=OFF",
                        "-DSDL2IMAGE_WEBP=OFF", "-DSDL2IMAGE_JXL=OFF",
                        "-DSDL2IMAGE_DEPS_SHARED=OFF", "-DSDL2IMAGE_VENDORED=OFF")
    configure_and_build(mixer, mixer_out, *common, sdl_lib, sdl_headers, no_host_sdl,
                        "-DBUILD_SHARED_LIBS=OFF", "-DSDL2MIXER_SAMPLES=OFF",
                        "-DSDL2MIXER_VENDORED=OFF", "-DSDL2MIXER_DEPS_SHARED=OFF",
                        "-DSDL2MIXER_MOD=OFF", "-DSDL2MIXER_OPUS=OFF",
                        "-DSDL2MIXER_WAVPACK=OFF", "-DSDL2MIXER_MIDI_FLUIDSYNTH=OFF",
                        "-DSDL2MIXER_MIDI_NATIVE=OFF")
    pc = cache / f"pkgconfig-{suffix}"
    pc.mkdir(exist_ok=True)
    write_pc(pc / "sdl2.pc", "sdl2", VERSIONS["SDL2"][0], sdl / "include", sdl_out, "-lSDL2 -lSDL2main")
    write_pc(pc / "physfs.pc", "physfs", VERSIONS["physfs"][0], physfs / "src", physfs_out, "-lphysfs -lz")
    write_pc(pc / "SDL2_image.pc", "SDL2_image", VERSIONS["SDL2_image"][0], image / "include", image_out, "-lSDL2_image")
    write_pc(pc / "SDL2_mixer.pc", "SDL2_mixer", VERSIONS["SDL2_mixer"][0], mixer / "include", mixer_out, "-lSDL2_mixer")
    return pc, sdk



def package_music(resource_root: Path, data_root: Path, game: str, *, keep_original_names: bool = False) -> None:
    music = resource_root / "Music"
    if music.exists():
        shutil.rmtree(music)
    tracks = sorted((data_root / "Music" / game).glob("*.mp3"))
    if not tracks:
        return

    numbered: dict[int, Path] = {}
    for path in tracks:
        prefix = path.name.split(" ", 1)[0]
        if prefix.isdigit():
            numbered[int(prefix)] = path

    music.mkdir(parents=True, exist_ok=True)
    if keep_original_names:
        for path in tracks:
            shutil.copy2(path, music / path.name)

    roles: dict[str, int] = {}
    level_numbers: list[int] = []
    if game == "D1":
        # D1 Redbook semantics: 2 title, 3 briefing, 4 end-level,
        # 5 credits, 6..N-1 levels, final track endgame.
        roles = {"title": 2, "briefing": 3, "endlevel": 4, "credits": 5}
        if numbered:
            last_track = max(numbered)
            roles["endgame"] = last_track
            level_numbers = [n for n in sorted(numbered) if 6 <= n < last_track]
    else:
        # D2 Redbook semantics: 2 title, 3 credits, 4+ level tracks.
        roles = {"title": 2, "credits": 3}
        level_numbers = [n for n in sorted(numbered) if n >= 4]

    for role, number in roles.items():
        if path := numbered.get(number):
            shutil.copy2(path, music / f"{role}.mp3")

    if level_numbers:
        levels = music / "Levels"
        levels.mkdir(parents=True, exist_ok=True)
        playlist = []
        for number in level_numbers:
            path = numbered[number]
            track_name = f"{number:02d}.mp3"
            shutil.copy2(path, levels / track_name)
            playlist.append(f"Music/Levels/{track_name}")
        (music / "Levels.m3u").write_text("\n".join(playlist) + "\n")


def bundle_game(build, game, data_root, target_os, platform, signing_identity, provisioning_profile):
    short = game.lower()
    binary = build / f"{short}x-rebirth" / f"{short}x-rebirth"
    app = build / f"{game}X-Rebirth.app"
    if app.exists():
        shutil.rmtree(app)
    app.mkdir(parents=True)
    shutil.copy2(binary, app / binary.name)
    source_data = data_root / game
    if not source_data.is_dir():
        raise RuntimeError(f"Licensed game data folder is missing: {source_data}")
    required = ("descent.hog", "descent.pig") if game == "D1" else (
        "DESCENT2.HOG", "DESCENT2.HAM", "DESCENT2.S22", "groupa.pig",
        "alien1.pig", "alien2.pig", "fire.pig", "ice.pig", "water.pig", "hoard.ham")
    available = {path.name.casefold() for path in source_data.iterdir() if path.is_file()}
    missing = [name for name in required if name.casefold() not in available]
    if missing:
        raise RuntimeError(f"Missing {game} game data: {', '.join(missing)}")
    resource_root = app
    d2_mission_stems = {path.stem.casefold() for path in source_data.iterdir()
                        if game == "D1" and path.is_file() and path.suffix.casefold() == ".mn2"}
    for path in source_data.iterdir():
        if not path.is_file() or path.name.startswith("."):
            continue
        if game == "D1" and (path.suffix.casefold() == ".mn2" or
                             (path.suffix.casefold() == ".hog" and path.stem.casefold() in d2_mission_stems)):
            continue
        shutil.copy2(path, resource_root / path.name)

    controller_db = ROOT / "contrib" / "gamecontrollerdb.txt"
    if not controller_db.is_file():
        raise RuntimeError(f"Missing SDL controller mapping database: {controller_db}")
    controller_text = controller_db.read_text()
    if target_os == "tvos":
        # The bundled SDL DB has Apple controller mappings tagged platform:iOS.
        # SDL reports tvOS as a distinct platform, so mirror those records with
        # the tvOS platform tag while retaining the canonical iOS originals.
        tvos_lines = [line.replace("platform:iOS,", "platform:tvOS,")
                      for line in controller_text.splitlines() if "platform:iOS," in line]
        controller_text += "\n" + "\n".join(tvos_lines) + "\n"
    (resource_root / "gamecontrollerdb.txt").write_text(controller_text)

    package_music(resource_root, data_root, game)

    # Apple required-reason API declaration for APIs used by the linked game
    # and dependency stack.  Keep this generated with the bundle so simulator,
    # device, iOS and tvOS packages stay in sync.
    privacy_info = {
        "NSPrivacyTracking": False,
        "NSPrivacyTrackingDomains": [],
        "NSPrivacyCollectedDataTypes": [],
        "NSPrivacyAccessedAPITypes": [
            {
                "NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryFileTimestamp",
                "NSPrivacyAccessedAPITypeReasons": ["C617.1"],
            },
            {
                "NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategorySystemBootTime",
                "NSPrivacyAccessedAPITypeReasons": ["35F9.1"],
            },
        ],
    }
    with (resource_root / "PrivacyInfo.xcprivacy").open("wb") as f:
        plistlib.dump(privacy_info, f, sort_keys=False)

    info = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleDisplayName": f"Descent {game[-1]}",
        "CFBundleExecutable": binary.name,
        "CFBundleIdentifier": f"org.dxx-rebirth.{short}x-{target_os}",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": f"{game}X-Rebirth",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.61.0",
        "CFBundleVersion": "1",
        "MinimumOSVersion": "15.0",
        "UIRequiresFullScreen": True,
        "UIApplicationSupportsIndirectInputEvents": True,
        "UIDeviceFamily": [1, 2] if target_os == "ios" else [3],
        "NSLocalNetworkUsageDescription": "Descent uses the local network to discover and join multiplayer games on your LAN.",
    }
    if target_os == "ios":
        info.update({
            "LSRequiresIPhoneOS": True,
            "UISupportedInterfaceOrientations": ["UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"],
            "UISupportedInterfaceOrientations~ipad": ["UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"],
            "UILaunchScreen": {},
        })
    info["UIApplicationSceneManifest"] = {
        "UIApplicationSupportsMultipleScenes": False,
        "UISceneConfigurations": {
            "UIWindowSceneSessionRoleApplication": [{
                "UISceneConfigurationName": "SDLSceneConfiguration",
                "UISceneDelegateClassName": "SDLUIKitSceneDelegate",
            }],
        },
    }
    icon_source = data_root / "Icons" / game / "Assets.xcassets"
    icon_set = "AppIcon.appiconset"
    if target_os == "tvos":
        tvos_icon_source = data_root / "Icons" / game / "tvOS" / "Assets.xcassets"
        if tvos_icon_source.is_dir():
            icon_source = tvos_icon_source
            icon_set = "AppIcon.brandassets"
    if not (icon_source / icon_set).is_dir():
        raise RuntimeError(f"Missing {game} app icon catalog: {icon_source / icon_set}")
    icon_info = build / f"{short}x-icon-info.plist"
    actool_platform = (
        "iphonesimulator" if target_os == "ios" and platform == "simulator" else
        "iphoneos" if target_os == "ios" else
        "appletvsimulator" if platform == "simulator" else "appletvos"
    )
    target_devices = ("iphone", "ipad") if target_os == "ios" else ("tv",)
    actool_args = [
        "xcrun", "actool", "--compile", app,
        "--platform", actool_platform,
        "--minimum-deployment-target", "15.0",
    ]
    for device in target_devices:
        actool_args.extend(("--target-device", device))
    actool_args.extend(("--app-icon", "AppIcon", "--output-partial-info-plist", icon_info, icon_source))
    run(*actool_args)
    info.update(plistlib.loads(icon_info.read_bytes()))
    with (app / "Info.plist").open("wb") as f:
        plistlib.dump(info, f)
    if provisioning_profile:
        shutil.copy2(provisioning_profile, app / "embedded.mobileprovision")
    if signing_identity:
        profile = subprocess.run(
            ["openssl", "cms", "-verify", "-inform", "DER", "-noverify", "-in", str(provisioning_profile)],
            check=True, capture_output=True,
        )
        profile_data = plistlib.loads(profile.stdout)
        profile_entitlements = profile_data["Entitlements"]
        profile_app_id = profile_entitlements.get("application-identifier", "")
        if "." not in profile_app_id:
            raise RuntimeError("Provisioning profile has no usable application-identifier")
        app_id_prefix, profile_bundle_pattern = profile_app_id.split(".", 1)
        bundle_id = info["CFBundleIdentifier"]
        if profile_bundle_pattern != "*":
            if profile_bundle_pattern.endswith(".*"):
                if not bundle_id.startswith(profile_bundle_pattern[:-1]):
                    raise RuntimeError(f"Provisioning profile does not match {bundle_id}")
            elif profile_bundle_pattern != bundle_id:
                raise RuntimeError(f"Provisioning profile does not match {bundle_id}")

        # Materialize only the entitlements the app actually needs.  A
        # provisioning profile is an allow-list, not a template that should be
        # copied wholesale into the app signature.
        entitlements = {"application-identifier": f"{app_id_prefix}.{bundle_id}"}
        for key in ("com.apple.developer.team-identifier", "get-task-allow"):
            if key in profile_entitlements:
                entitlements[key] = profile_entitlements[key]
        if profile_entitlements.get("com.apple.developer.networking.multicast"):
            entitlements["com.apple.developer.networking.multicast"] = True
        entitlements_path = build / f"{short}x-entitlements.plist"
        with entitlements_path.open("wb") as f:
            plistlib.dump(entitlements, f)
        run("codesign", "--force", "--sign", signing_identity,
            "--entitlements", entitlements_path, "--timestamp=none", app)
    print(f"Built {app} ({target_os} {platform})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-os", choices=("ios", "tvos"), default="ios")
    parser.add_argument("--platform", choices=("simulator", "device"), default="simulator")
    parser.add_argument("--data-root", type=Path, default=ROOT / "private assets")
    parser.add_argument("--cache", type=Path, default=Path("/private/tmp/rebirth-ios-deps"))
    parser.add_argument("--signing-identity", help="Apple Development certificate for device installation")
    parser.add_argument("--provisioning-profile-d1", type=Path, help="matching Descent 1 development provisioning profile")
    parser.add_argument("--provisioning-profile-d2", type=Path, help="matching Descent 2 development provisioning profile")
    args = parser.parse_args()
    profiles = {"D1": args.provisioning_profile_d1, "D2": args.provisioning_profile_d2}
    if args.platform == "device" and (args.signing_identity or any(profiles.values())) and not (args.signing_identity and all(profiles.values())):
        parser.error("device signing requires --signing-identity and both game provisioning profiles")
    if args.platform == "simulator" and (args.signing_identity or any(profiles.values())):
        parser.error("simulator bundles do not need device signing")
    cache = args.cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    pc, sdk = build_dependencies(cache, args.target_os, args.platform)
    if args.target_os == "ios":
        target = "arm64-apple-ios15.0-simulator" if args.platform == "simulator" else "arm64-apple-ios15.0"
        wrapper_suffix = args.platform
        build_name = f"build-ios-{args.platform}"
    else:
        target = "arm64-apple-tvos15.0-simulator" if args.platform == "simulator" else "arm64-apple-tvos15.0"
        wrapper_suffix = f"tvos-{args.platform}"
        build_name = f"build-tvos-{args.platform}"
    wrapper = cache / f"clangxx-{wrapper_suffix}"
    wrapper.write_text(f'#!/bin/sh\nexec /usr/bin/clang++ -target {target} -isysroot "$(xcrun --sdk {sdk} --show-sdk-path)" "$@" -Wno-error=unused-result\n')
    wrapper.chmod(0o755)
    env = os.environ.copy()
    env["PKG_CONFIG_PATH"] = ""
    env["PKG_CONFIG_LIBDIR"] = str(pc)
    build = ROOT / build_name
    run("scons", "-j4", "host_platform=ios", f"apple_mobile_target={args.target_os}",
        f"builddir={build.name}", f"CXX={wrapper}",
        "sdlimage=1", "sdlmixer=1", "screenshot=none", "lto=0", "git_status=0",
        "git_describe_version=0", "build_metadata=0",
        "macos_add_frameworks=0", "macos_bundle_libs=0", env=env)
    for game in ("D1", "D2"):
        bundle_game(build, game, args.data_root.resolve(), args.target_os, args.platform,
                    args.signing_identity, profiles[game])


if __name__ == "__main__":
    main()
