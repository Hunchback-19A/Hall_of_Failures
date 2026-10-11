/*
* PSCF - Polymer Self-Consistent Field
*
* Copyright 2015 - 2025, The Regents of the University of Minnesota
* Distributed under the terms of the GNU General Public License.
*
* Modified 7 October 2026 by Disquietude.
* On Windows, space-group files are read from data/groups beside the
* executable, or from ../data/groups when the executable is in bin/.
*/

#include "groupFile.h"
#include <pscf/paths.h>
#include <util/global.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string>
#endif

// Macros to generated quoted path to data directory, DAT_DIR
#define XSTR(s) STR(s)
#define STR(s) # s
#define DAT_DIR_STRING XSTR(PSCF_DATA_DIR)
//#define DAT_DIR_STRING XSTR(DAT_DIR)

namespace Pscf { 
namespace Prdc { 

   using namespace Util;

#ifdef _WIN32
   /*
   * Directory containing data/groups, based on where this exe lives.
   */
   std::string windowsDataDir()
   {
      char path[MAX_PATH];
      DWORD n = GetModuleFileNameA(nullptr, path, MAX_PATH);
      if (n > 0 && n < MAX_PATH) {
         std::string exe(path, n);
         std::string::size_type slash = exe.find_last_of("\\/");
         if (slash != std::string::npos) {
            std::string dir = exe.substr(0, slash + 1);
            std::string beside = dir + "data\\";
            std::string parent = dir + "..\\data\\";
            std::string probe = beside + "groups\\1";
            DWORD attr = GetFileAttributesA(probe.c_str());
            if (attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY)) {
               return beside;
            }
            return parent;
         }
      }
      return std::string(DAT_DIR_STRING);
   }
#endif

   /*
   * Generates the file name from a group name.
   */
   std::string makeGroupFileName(int D, std::string groupName)
   {
#ifdef _WIN32
      std::string filename = windowsDataDir();
#else
      std::string filename = DAT_DIR_STRING ;
#endif
      filename += "groups/";
      if (D==1) {
         filename += "1/";
      } else
      if (D==2) {
         filename += "2/";
      } else
      if (D==3) {
         filename += "3/";
      } else {
         UTIL_THROW("Invalid dimension of space");
      }
      filename += groupName;
      return filename;
   }

} // namespace Prdc
} // namespace Pscf
