#include "dzplugin.h"
#include "dzapp.h"

#include "version.h"
#include "DzRobloxAction.h"
#include "DzRobloxDialog.h"

#include "dzbridge.h"

CPP_PLUGIN_DEFINITION("Daz To Roblox Exporter");

DZ_PLUGIN_AUTHOR("Daz 3D, Inc");

DZ_PLUGIN_VERSION(PLUGIN_MAJOR, PLUGIN_MINOR, PLUGIN_REV, PLUGIN_BUILD);

DZ_PLUGIN_DESCRIPTION(QString(
"This plugin provides the ability to send assets to Roblox Studio. \
Documentation and source code are available on <a href = \"https://github.com/daz3d/DazToRoblox\">Github</a>.<br>"
));

DZ_PLUGIN_CLASS_GUID(DzRobloxAction, cffcd78e-3917-4b77-a60f-c559753226ee);
NEW_PLUGIN_CUSTOM_CLASS_GUID(DzRobloxDialog, 0ab8fdb4-6575-4a7c-ad4b-456a687c1c81);

#ifdef UNITTEST_DZBRIDGE

#include "UnitTest_DzRobloxAction.h"
#include "UnitTest_DzRobloxDialog.h"

DZ_PLUGIN_CLASS_GUID(UnitTest_DzRobloxAction, de0a7ebe-2a0e-4d2c-809d-fcee4807a4d1);
DZ_PLUGIN_CLASS_GUID(UnitTest_DzRobloxDialog, cb4243ad-bf17-4d76-a7a1-0b6790b4c14d);

#endif
