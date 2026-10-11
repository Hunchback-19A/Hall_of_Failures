/*
* PSCF - Polymer Self-Consistent Field
*
* Copyright 2015 - 2025, The Regents of the University of Minnesota
* Distributed under the terms of the GNU General Public License.
*/

#include "WFields.h"               // class header
#include <rpc/field/FieldIo.tpp>
#include <pscf/cpu/VecOp.h>
#include <rp/field/WFields.tpp>    // base class implementation

// Explicit instantiation definitions
namespace Pscf {
   namespace Rp {
      using namespace Prdc;
      template class Rp::WFields<1, Cpu::RField<1>, Rpc::FieldIo<1> >;
      template class Rp::WFields<2, Cpu::RField<2>, Rpc::FieldIo<2> >;
      template class Rp::WFields<3, Cpu::RField<3>, Rpc::FieldIo<3> >;
   }
   namespace Rpc {
      template class WFields<1>;
      template class WFields<2>;
      template class WFields<3>;
   }
}
