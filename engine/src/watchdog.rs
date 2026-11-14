extern crate device_query;
use device_query::{DeviceState, Keycode};

use crate::hooks;

#[static_init::dynamic]
static mut KILL: bool = false;

/// 打鍵を見にいく間隔。これより短い打鍵は取りこぼす
const POLL_MS: u64 = 25;

pub fn install() {
  std::thread::spawn(move || {
    let state = DeviceState::new();
    let mut hook_enabled: bool = true;
    let mut was_down: bool = false;

    // TODO: only disable hook after render loop
    while !*KILL.read() {
      let keys = state.query_keymap();
      // Ctrl は左右どちらでもよい
      let down = keys.contains(&Keycode::F2)
        && (keys.contains(&Keycode::LControl) || keys.contains(&Keycode::RControl));

      // 押している間ずっと切り替わってしまわないよう、押した瞬間だけを拾う。
      // 以前は「今押されているか」だけを 150ms ごとに見ていたため、
      // 短い打鍵は取りこぼし、長めの打鍵は2回切り替わって元に戻っていた
      if down && !was_down {
        if hook_enabled {
          hook_enabled = false;
          log::info!("日本語化を無効にしました");
          let _ = unsafe { hooks::disable_all() };
        } else {
          hook_enabled = true;
          log::info!("日本語化を有効にしました");
          let _ = unsafe { hooks::enable_all() };
        }
      }
      was_down = down;

      std::thread::sleep(std::time::Duration::from_millis(POLL_MS));
    }
  });
}

pub fn uninstall() {
  *KILL.write() = true;
}
