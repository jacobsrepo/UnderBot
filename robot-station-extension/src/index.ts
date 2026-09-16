import { ExtensionContext } from "@foxglove/extension";

import { initStation } from "./station";

export function activate(extensionContext: ExtensionContext): void {
  extensionContext.registerPanel({ name: "UnderBot Controls", initPanel: initStation });
}
