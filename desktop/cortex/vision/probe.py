"""
Active Closed-Loop Optical Pin Discovery Probe
Tests each Arduino pin (D2 to D13, A0 to A5) in both HIGH and LOW states,
capturing camera frames to measure physical light emission changes.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Callable


class HardwareVisionProbe:
    def __init__(self, serial_device, camera):
        self.device = serial_device
        self.camera = camera
        self.pins_to_test = [
            "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12", "D13",
            "A0", "A1", "A2", "A3", "A4", "A5"
        ]

    async def auto_discover_led_pin(
        self,
        target_color: str = "blue",
        on_progress_cb: Optional[Callable[[str], Any]] = None
    ) -> Dict[str, Any]:
        """
        Actively probes each pin and checks live camera feed for optical emission changes.
        """
        color_key = target_color.lower().strip()
        target_field = "blue_hotspot_pixels" if "blue" in color_key else ("green_hotspot_pixels" if "green" in color_key else "red_hotspot_pixels")
        glowing_field = "blue_glowing" if "blue" in color_key else ("green_glowing" if "green" in color_key else "red_glowing")

        # 1. Turn all pins OFF as baseline
        self.device.set_all_pins(0)
        await asyncio.sleep(0.3)

        # Measure baseline optical readings
        baseline = self.camera.analyze_optical_emissions()
        base_pixels = baseline.get(target_field, 0)

        discovered = []

        # 2. Test each pin in HIGH state (Active HIGH)
        for pin in self.pins_to_test:
            if on_progress_cb:
                await on_progress_cb(f"Probing {pin} [HIGH]...")

            self.device.set_pin(pin, 1)
            await asyncio.sleep(0.25)

            # Analyze live optical frame
            optical = self.camera.analyze_optical_emissions()
            pixels = optical.get(target_field, 0)
            delta = pixels - base_pixels

            if delta > 80 or optical.get(glowing_field):
                discovered.append({
                    "pin": pin,
                    "state": "HIGH (Active HIGH)",
                    "color": target_color,
                    "delta_pixels": delta,
                    "verified": True
                })
                # Keep discovered pin state for confirmation or reset
                self.device.set_pin(pin, 0)
                await asyncio.sleep(0.15)
                break

            self.device.set_pin(pin, 0)
            await asyncio.sleep(0.1)

        # 3. If not found in Active HIGH, test Active LOW (many LED shields are common-anode / active-low)
        if not discovered:
            # Set all pins HIGH as baseline for active-low
            self.device.set_all_pins(1)
            await asyncio.sleep(0.3)
            baseline_high = self.camera.analyze_optical_emissions()
            base_high_pixels = baseline_high.get(target_field, 0)

            for pin in self.pins_to_test:
                if on_progress_cb:
                    await on_progress_cb(f"Probing {pin} [LOW / Active-Low]...")

                self.device.set_pin(pin, 0)
                await asyncio.sleep(0.25)

                optical = self.camera.analyze_optical_emissions()
                pixels = optical.get(target_field, 0)
                delta = pixels - base_high_pixels

                if delta > 80 or optical.get(glowing_field):
                    discovered.append({
                        "pin": pin,
                        "state": "LOW (Active LOW / Common Anode)",
                        "color": target_color,
                        "delta_pixels": delta,
                        "verified": True
                    })
                    break

                self.device.set_pin(pin, 1)
                await asyncio.sleep(0.1)

            # Reset all pins to OFF
            self.device.set_all_pins(0)

        if discovered:
            hit = discovered[0]
            return {
                "success": True,
                "target_color": target_color,
                "pin": hit["pin"],
                "polarity": hit["state"],
                "delta_pixels": hit["delta_pixels"],
                "summary": f"Optical probe successfully identified that {hit['pin']} controls the {target_color.upper()} LEDs (verified by camera emission detection with +{hit['delta_pixels']} pixels)."
            }

        return {
            "success": False,
            "target_color": target_color,
            "tested_pins": self.pins_to_test,
            "summary": f"Tested all 16 pins (D2 through A5) in both Active-HIGH and Active-LOW states. The camera did not detect any physical {target_color} light emission changes."
        }
