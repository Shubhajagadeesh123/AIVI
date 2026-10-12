/* ==========================================
   BlindMate battery alerts

   Speaks when the phone battery gets low (20%, 10%, 5%) so a blind user
   is never surprised by a dead phone, announces when a charger is
   connected or removed, and answers "how much battery do I have?".

   Uses the Battery Status API. Chrome on Android supports it; iPhone
   (Safari) and Firefox do not, and there the feature simply stays quiet.
========================================== */
(function () {
  const THRESHOLDS = [20, 10, 5];

  class BatteryMonitor {
    constructor() {
      this.battery = null;
      this.announced = new Set(); // thresholds already spoken this discharge
      this.lastCharging = null;
      this.supported = "getBattery" in navigator;
      if (this.supported) this.init();
    }

    async init() {
      try {
        this.battery = await navigator.getBattery();
      } catch (e) {
        this.supported = false;
        return;
      }
      const b = this.battery;
      this.lastCharging = b.charging;
      b.addEventListener("levelchange", () => this.onLevel());
      b.addEventListener("chargingchange", () => this.onCharging());

      // If the phone is already low when the app opens, say so once,
      // after the greeting has had time to finish.
      setTimeout(() => this.onLevel(true), 15000);
    }

    get level() {
      return this.battery ? Math.round(this.battery.level * 100) : null;
    }

    get charging() {
      return this.battery ? !!this.battery.charging : null;
    }

    /** {level, charging} or null - used by the SOS alert. */
    snapshot() {
      return this.battery ? { level: this.level, charging: this.charging } : null;
    }

    say(kind, n, urgent) {
      if (!window.BM) return;
      const { en, local } = window.BM.batteryText(kind, n);
      window.BM.speakSafe(en, { local, queue: !urgent });
    }

    onLevel(startup) {
      if (!this.battery || this.charging) return;
      const lvl = this.level;

      // back above all thresholds -> allow warnings again next time
      THRESHOLDS.forEach((t) => {
        if (lvl > t) this.announced.delete(t);
      });

      // lowest threshold we've crossed that hasn't been spoken yet
      const crossed = THRESHOLDS.filter((t) => lvl <= t && !this.announced.has(t));
      if (crossed.length === 0) return;
      THRESHOLDS.forEach((t) => {
        if (lvl <= t) this.announced.add(t); // don't repeat the higher ones later
      });

      const lowest = Math.min(...crossed);
      if (lowest <= 10) this.say("critical", lvl, true);
      else this.say("low", lvl, false);
    }

    onCharging() {
      if (!this.battery) return;
      const now = this.charging;
      if (now === this.lastCharging) return;
      this.lastCharging = now;
      if (now) {
        this.announced.clear();
        this.say("on", this.level, false);
      } else {
        this.say("off", this.level, false);
        this.onLevel();
      }
    }

    /** Spoken answer to "how much battery do I have?" */
    report() {
      if (!window.BM) return;
      if (!this.battery) {
        const { en, local } = window.BM.batteryText("unsupported", 0);
        window.BM.speakSafe(en, { local });
        return;
      }
      const { en, local } = window.BM.batteryText(
        this.charging ? "charging" : "status",
        this.level,
      );
      window.BM.speakSafe(en, { local });
    }
  }

  window.addEventListener("DOMContentLoaded", () => {
    window.BMBattery = new BatteryMonitor();
  });
})();