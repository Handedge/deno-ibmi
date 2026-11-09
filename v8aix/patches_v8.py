# AIX (IBM i PASE) patches to the rusty_v8 / V8 sources for cross-compilation
# with clang from Linux. Idempotent.
# Usage: python3 patches_v8.py <rusty_v8 root>
import pathlib
import sys

R = pathlib.Path(sys.argv[1])
BS = chr(92)  # backslash, to write C strings without escaping pitfalls


def replace(f, old, new):
    t = f.read_text()
    if new in t:
        return
    assert old in t, f"motif absent de {f}"
    f.write_text(t.replace(old, new, 1))
    print("patched:", f)


# --- Cross toolchain (Chromium build/) --------------------------------------
# Chromium clang targeting AIX; AIX archives via llvm-ar (ar-aix wrapper);
# AIX executables (mksnapshot, d8) are linked on IBM i (lien-aix.sh records
# the command). LINUXBUILD paths (~/v8aix).
replace(R / "build/toolchain/aix/BUILD.gn", '    is_clang = false\n  }\n}\n',
          '    is_clang = false\n  }\n}\n'
          '\n'
          '# deno-ibmi : compilation croisée depuis Linux x86_64 vers AIX / IBM i PASE avec le\n'
          '# clang de Chromium ; les exécutables sont liés sur IBM i (lien-aix.sh enregistre).\n'
          'clang_toolchain_prefix = rebase_path("$clang_base_path/bin/", root_build_dir)\n'
          'gcc_toolchain("clang_ppc64") {\n'
          '  cc = clang_toolchain_prefix + "clang --target=powerpc64-ibm-aix7.2"\n'
          '  cxx = clang_toolchain_prefix + "clang++ --target=powerpc64-ibm-aix7.2"\n'
          '  readelf = clang_toolchain_prefix + "llvm-readobj"\n'
          '  nm = clang_toolchain_prefix + "llvm-nm"\n'
          '  ar = "/home/build/v8aix/bin/ar-aix"\n'
          '  asm = "/home/build/v8aix/bin/asm-aix"\n'
          '  ld = "/home/build/v8aix/lien-aix.sh"\n'
          '  toolchain_args = {\n'
          '    current_cpu = "ppc64"\n'
          '    current_os = "aix"\n'
          '    use_remoteexec = false\n'
          '    is_clang = true\n'
          '  }\n'
          '}\n')

# Chromium AIX flags are written for gcc: clang variant (PASE headers from
# ~/v8aix/sysroot/usr/include, __COMPATMATH__ against the C++ overloads in the
# AIX math.h that clash with those of libc++)
replace(R / "build/config/aix/BUILD.gn",
          '    "-mcpu=power5+",\n    "-mfprnd",\n    "-mno-popcntb",\n    "-maix64",\n'
          '    "-fdata-sections",\n    "-ffunction-sections",\n'
          '    "-fno-extern-tls-init",\n    "-fno-reorder-functions",\n    "-O3",\n',
          '    "-fdata-sections",\n    "-ffunction-sections",\n    "-O3",\n')
replace(R / "build/config/aix/BUILD.gn", '  cflags_cc = [\n',
          '  if (is_clang) {\n'
          '    # deno-ibmi : compilation croisée (clang de Chromium, en-têtes PASE)\n'
          '    cflags += [\n'
          '      "--sysroot=/home/build/v8aix/sysroot",\n'
          '      "-mcpu=pwr8",\n'
          '      "-D__COMPATMATH__",\n'
          '      "-D_THREAD_SAFE",\n'
          '      # sémantique #pragma pack standard (clang applique par défaut celle\n'
          '      # du compilateur XL d IBM sur AIX) ; option retenue par Node et Chromium\n'
          '      "-fno-xl-pragma-pack",\n'
          '      # IBM i PASE (défini d office par le gcc d IBM i, pas par clang) : V8 en\n'
          '      # dépend pour le décalage des adresses du tas (0x07...) de JSDispatchTable,\n'
          '      # l horloge CPU par fil et la détection du processeur\n'
          '      "-D__PASE__",\n'
          '    ]\n'
          '  } else {\n'
          '    cflags += [\n'
          '      "-mcpu=power5+",\n'
          '      "-mfprnd",\n'
          '      "-mno-popcntb",\n'
          '      "-maix64",\n'
          '      "-fno-extern-tls-init",\n'
          '      "-fno-reorder-functions",\n'
          '    ]\n'
          '  }\n'
          '  cflags_cc = [\n')
# "large" code model: the V8 TOC (~2.9 MB) exceeds the 64 KB addressable in the
# small model. With -bbigtoc, the PASE linker crashes (0711-759 save.c line 965)
# on a 326 MB executable such as Deno; with large, TOC accesses use 32-bit
# offsets (addis + ld) and no longer need a linker fixup.
replace(R / "build/config/aix/BUILD.gn",
          '      "-mcpu=pwr8",\n      "-D__COMPATMATH__",\n',
          '      "-mcpu=pwr8",\n      "-mcmodel=large",\n      "-D__COMPATMATH__",\n')


# cppgc: the AIX inline assembly (.csect, .globl x, hidden) is not understood by
# the LLVM XCOFF parser. With clang, __builtin_unwind_init() forces all
# callee-saved registers (r14-r31) to be spilled into the current frame;
# the callback is then called with the stack pointer, as in the assembly
# version.
p = R / "v8/src/heap/base/asm/ppc/push_registers_asm.cc"
replace(p, "asm(\n#if defined(_AIX)", """#if defined(_AIX) && defined(__clang__)
// deno-ibmi : version C++ pour clang (cible AIX, compilation croisée)
#include <cstdint>
namespace heap::base { class Stack; }
extern "C" __attribute__((noinline)) void PushAllRegistersAndIterateStack(
    heap::base::Stack* stack, void* argument,
    void (*callback)(heap::base::Stack*, void*, const void*)) {
  __builtin_unwind_init();  // registres préservés sauvegardés dans ce cadre
  callback(stack, argument, __builtin_frame_address(0));
  asm volatile("" ::: "memory");  // pas d'appel terminal : le cadre reste vivant
}
#else
asm(
#if defined(_AIX)""")
end = '    "  blr                                             ' + BS + 'n");\n'
t = p.read_text()
if not t.rstrip().endswith("#endif  // _AIX && __clang__"):
    assert t.endswith(end), "fin de push_registers_asm.cc inattendue"
    p.write_text(t + "#endif  // _AIX && __clang__\n")
    print("patched:", p, "(#endif)")

# simdutf: rusty_v8 only exposes the "le" UTF-16 variants, while Deno passes them
# u16 buffers in native byte order. On big-endian POWER, "t" (0x0074) became
# "琀" (0x7400): SyntaxError as soon as a source contains non-ASCII text.
# On big-endian, the wrappers call the "be" variants (= native order).
import re
b = R / "src/binding.cc"
t = b.read_text()
if "DENO_U16" not in t:
    start = t.index("bool simdutf__validate_utf16le(")
    body = re.sub(r"simdutf::(\w*?)utf16le(\w*)", r"simdutf::DENO_U16(\1utf16,\2)", t[start:])
    header = ("// deno-ibmi : UTF-16 dans l'ordre natif (big-endian sur IBM i / AIX)\n"
              "#if defined(__BIG_ENDIAN__) || (defined(__BYTE_ORDER__) && __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__)\n"
              "#define DENO_U16(a, b) a##be##b\n#else\n#define DENO_U16(a, b) a##le##b\n#endif\n")
    b.write_text(t[:start] + header + body)
    print("patched:", b, "(native UTF-16 simdutf)")


# Maglev POWER: TestUint8AndJumpIfAnySet / AllClear load 32 bits (LoadU32) at the address
# of a one-byte field, then apply an 8-bit mask. On little-endian (ppc64le, the only target
# V8 tests) the intended byte is the low-order one: correct by accident. On big-endian
# (AIX, IBM i) the following byte gets tested: `typeof undefined == 'undefined'`
# returned false under Maglev (IsUndetectable bit of Map::bit_field never seen), hence
# unicode-test.js failures and NaN counters. Load a single byte instead (like lbz elsewhere,
# and tmy on s390x, the other big-endian target).
m = R / "v8/src/maglev/ppc/maglev-assembler-ppc-inl.h"
t = m.read_text()
if "deno-ibmi : octet" not in t:
    for fn in ("TestUint8AndJumpIfAnySet", "TestUint8AndJumpIfAllClear"):
        start = t.index("inline void MaglevAssembler::" + fn + "(\n    MemOperand operand")
        i = t.index("LoadU32(r0, operand);", start)
        t = t[:i] + "LoadU8(r0, operand);  // deno-ibmi : octet (big-endian)" + t[i + len("LoadU32(r0, operand);"):]
    m.write_text(t)
    print("patched:", m, "(TestUint8: LoadU8)")
# Same file: ContextCell::state_ is an int32_t (enum State : int32_t) but POWER reads
# it as 64 bits (LoadU64); on big-endian the state lands in the upper half and the
# comparisons fail (spurious deoptimization, maglev/load_mutable_heap_slot_*).
# s390x (big-endian) reads 32 bits.
replace(m, "  LoadU64(state, FieldMemOperand(cell, offsetof(ContextCell, state_)), r0);",
          "  LoadU32(state, FieldMemOperand(cell, offsetof(ContextCell, state_)),\n"
          "          r0);  // deno-ibmi : int32_t (big-endian)")


# Modulo (x % y) on AIX: V8 wraps fmod in feclearexcept/fetestexcept(FE_UNDERFLOW) and
# returns x if the underflow flag is raised. Under PASE this flag is unreliable:
# left set by an earlier computation (JIT code), it makes the function wrongly return x
# ((b % 4) - (a % 4) gave -12 under Maglev: unstable Float64Array sorts, comparators
# of resizable arrays), and 5e-324 % Number.MAX_VALUE gave 0 (div-mod.js).
# Version without floating-point exceptions: cases exact by definition (y infinite,
# |x| < |y|), then fmod, which is exact when |x| >= |y|.
u = R / "v8/src/utils/utils.h"
t = u.read_text()
if "deno-ibmi : sans exceptions flottantes" not in t:
    start = t.index("#elif defined(V8_OS_AIX)\n", t.index("inline double Modulo(double x, double y)"))
    end = t.index("#else\n  return std::fmod(x, y);", start)
    t = (t[:start] + "#elif defined(V8_OS_AIX)\n"
         "  // deno-ibmi : sans exceptions flottantes (fetestexcept non fiable sous PASE)\n"
         "  if (std::isfinite(x) && (std::isinf(y) || std::fabs(x) < std::fabs(y))) return x;\n"
         "  return std::fmod(x, y);\n" + t[end:])
    u.write_text(t)
    print("patched:", u, "(Modulo AIX)")


# Liftoff POWER (WebAssembly): atomic operations ignore their Endianness parameter
# and always byte-swap on big-endian. That is right for linear memory
# (little-endian), wrong for GC struct fields (native order, kNative):
# struct.atomic.rmw.cmpxchg on a reference byte-swapped the pointer -> SEGV
# (regress-504716006, -505117973, -508691168), and atomics on integer fields
# returned byte-swapped values. We honor endianness, and the pointer exchange passes
# kNative (like s390x, the other big-endian target).
f = R / "v8/src/wasm/baseline/ppc/liftoff-assembler-ppc-inl.h"
t = f.read_text()
if "kCibleBigEndian" not in t:
    t = t.replace("Endianness /* endianness */", "Endianness endianness")
    # AtomicLoad / AtomicStore: little-endian load/store only for kLittle
    t = t.replace("  Load(dst, src_addr, offset_reg, offset_imm, type, trapping_load_pc, true,\n"
                  "       i64_offset);\n  lwsync();",
                  "  Load(dst, src_addr, offset_reg, offset_imm, type, trapping_load_pc,\n"
                  "       endianness == kLittle, i64_offset);  // deno-ibmi\n  lwsync();", 1)
    t = t.replace("  Store(dst_addr, offset_reg, offset_imm, src, type, pinned, trapping_store_pc,\n"
                  "        true, i64_offset);\n  sync();",
                  "  Store(dst_addr, offset_reg, offset_imm, src, type, pinned, trapping_store_pc,\n"
                  "        endianness == kLittle, i64_offset);  // deno-ibmi\n  sync();", 1)
    t = t.replace("constexpr bool is_be = false;\n#endif\n",
                  "constexpr bool is_be = false;\n#endif\n"
                  "constexpr bool kCibleBigEndian = is_be;  // deno-ibmi\n", 1)
    # Add/Sub/And/Or/Xor: local is_be derived from endianness before the macro
    t = re.sub(r"\n  ATOMIC_OP\((\w+)\);",
               r"\n  const bool is_be = kCibleBigEndian && endianness == kLittle;  // deno-ibmi\n  ATOMIC_OP(\1);", t)
    # Exchange / CompareExchange: same thing at the top of the function
    for fn in ("void LiftoffAssembler::AtomicExchange(", "void LiftoffAssembler::AtomicCompareExchange("):
        d = t.index(fn)
        i = t.index("Endianness endianness) {\n", d) + len("Endianness endianness) {\n")
        t = t[:i] + "  const bool is_be = kCibleBigEndian && endianness == kLittle;  // deno-ibmi\n" + t[i:]
    old = ("      COMPRESS_POINTERS_BOOL ? StoreType::kI32Store : StoreType::kI64Store,\n"
              "      trapping_load_pc, false);")
    assert old in t
    t = t.replace(old, "      COMPRESS_POINTERS_BOOL ? StoreType::kI32Store : StoreType::kI64Store,\n"
                          "      trapping_load_pc, false, kNative);  // deno-ibmi : champ GC natif")
    f.write_text(t)
    print("patched:", f, "(Liftoff atomics: endianness)")


# Maglev: Float64Modulus is declared a "call node" (the register allocator then saves
# registers) only for ARM/ARM64/RISC-V/LoongArch, whereas POWER also implements it with a
# C call (mod_two_doubles_operation). Live volatile floating-point registers were
# clobbered whenever the C function used them (AIX libm, Modulo compiled by clang): a
# second modulo saw its divisor overwritten ((b % 4) - (a % 4) = -12; sorts of
# Float64Array and resizable arrays). ppc64 added to the list.
replace(R / "v8/src/maglev/maglev-ir.h",
          "#if defined(V8_TARGET_ARCH_ARM64) || defined(V8_TARGET_ARCH_ARM) || \\\n"
          "    defined(V8_TARGET_ARCH_RISCV64) || defined(V8_TARGET_ARCH_LOONG64)\n",
          "#if defined(V8_TARGET_ARCH_ARM64) || defined(V8_TARGET_ARCH_ARM) || \\\n"
          "    defined(V8_TARGET_ARCH_RISCV64) || defined(V8_TARGET_ARCH_LOONG64) || \\\n"
          "    defined(V8_TARGET_ARCH_PPC64)  // deno-ibmi : appel C aussi sur POWER\n")
# a call node defines MaxCallStackArgs (like Float64Exponentiate)
replace(R / "v8/src/maglev/ppc/maglev-ir-ppc.cc",
          "void Float64Modulus::SetValueLocationConstraints() {\n",
          "int Float64Modulus::MaxCallStackArgs() const { return 0; }  // deno-ibmi\n"
          "void Float64Modulus::SetValueLocationConstraints() {\n")


# IMMEDIATE_CRASH: ".vbyte" (an AIX assembler directive) is unknown to the
# LLVM XCOFF parser; 0x7D821008 = the trap instruction "tw 12,2,2".
replace(R / "v8/src/base/immediate-crash.h",
          '#define TRAP_SEQUENCE1_() asm volatile(".vbyte 4,0x7D821008");',
          '#if defined(__clang__)\n'
          '#define TRAP_SEQUENCE1_() asm volatile("tw 12,2,2");  // deno-ibmi : 0x7D821008\n'
          '#else\n'
          '#define TRAP_SEQUENCE1_() asm volatile(".vbyte 4,0x7D821008");\n'
          '#endif')

# V8 generators (torque, bytecode list, regexp special cases): built for the
# Linux x64 host targeting ppc64 (their output does not depend on byte
# order), whereas mksnapshot is built for AIX and run
# on IBM i.
replace(R / "build/toolchain/linux/BUILD.gn",
          'clang_v8_toolchain("clang_x64_v8_mips64el") {',
          'clang_v8_toolchain("clang_x64_v8_ppc64") {  # deno-ibmi\n'
          '  toolchain_args = {\n'
          '    current_cpu = "x64"\n'
          '    current_os = "linux"  # sinon hérité de la cible (aix)\n'
          '    v8_current_cpu = "ppc64"\n'
          '  }\n'
          '}\n\n'
          'clang_v8_toolchain("clang_x64_v8_mips64el") {')
replace(R / "v8/gni/snapshot_toolchain.gni",
          'v8_generator_toolchain = v8_snapshot_toolchain\n',
          'v8_generator_toolchain = v8_snapshot_toolchain\n'
          '# deno-ibmi : compilation croisée vers AIX, générateurs exécutés sur l\'hôte\n'
          'if (host_cpu == "x64" && target_os == "aix") {\n'
          '  v8_generator_toolchain = "//build/toolchain/linux:clang_x64_v8_ppc64"\n'
          '}\n')
replace(R / "v8/BUILD.gn",
          'if (current_toolchain == v8_snapshot_toolchain) {\n  v8_executable("torque") {',
          'if (current_toolchain == v8_generator_toolchain) {  # deno-ibmi (au lieu de snapshot)\n  v8_executable("torque") {')
# -mcpu=pwr9 only for code actually compiled for POWER (not for the
# x86_64 generators targeting ppc64)
replace(R / "v8/BUILD.gn",
          '    } else if (!v8_target_is_simulator) {\n      cflags += [ "-mcpu=pwr9" ]',
          '    } else if (!v8_target_is_simulator && current_cpu == "ppc64") {  # deno-ibmi\n      cflags += [ "-mcpu=pwr9" ]')
# llvm-nm rejects -X64 outside AIX

# gcc_toolchain.gni: the rules (ar -X64, -soname, --whole-archive...) test
# current_os, evaluated in the target context (aix) for every toolchain.
# Test each toolchain's own OS instead.
g = R / "build/toolchain/gcc_toolchain.gni"
t = g.read_text()
t2 = t.replace('if (current_os == "aix")', 'if (invoker_toolchain_args.current_os == "aix")')
t2 = t2.replace('if (current_os != "aix")', 'if (invoker_toolchain_args.current_os != "aix")')
if t2 != t:
    g.write_text(t2)
    print("patched:", g)


# Separate assembler for the AIX toolchain: gcc_toolchain always uses the
# C compiler as assembler; accept invoker.asm (asm-aix wrapper, which
# reuses the embedded.o assembled on IBM i).
replace(R / "build/toolchain/gcc_toolchain.gni",
          "    asm = invoker.cc\n",
          "    if (defined(invoker.asm)) {  # deno-ibmi\n      asm = invoker.asm\n    } else {\n      asm = invoker.cc\n    }\n")


# Physical memory on AIX: V8 reads sysconf(_SC_AIX_REALMEM), which fails under PASE (-1,
# errno 109). AmountOfPhysicalMemory() therefore returned -1024 and V8 fell back to its
# minimum heap limit (heap_size_limit 262 MB on a 64 GB machine: "Fatal JavaScript out
# of memory: Reached heap limit" in streams_test). getsystemcfg(SC_PHYSMEM) answers
# correctly under PASE (68,719,476,736 on IBMI).
s = R / "v8/src/base/sys-info.cc"
replace(s, "#if V8_OS_BSD\n#include <sys/sysctl.h>\n#endif\n",
          "#if V8_OS_BSD\n#include <sys/sysctl.h>\n#endif\n"
          "#if V8_OS_AIX\n#include <sys/systemcfg.h>  // deno-ibmi : getsystemcfg\n#endif\n")
replace(s, "#elif V8_OS_AIX\n  int64_t result = sysconf(_SC_AIX_REALMEM);\n"
             "  return static_cast<int64_t>(result) * 1024L;\n",
          "#elif V8_OS_AIX\n  int64_t result = sysconf(_SC_AIX_REALMEM);\n"
          "  if (result > 0) return static_cast<int64_t>(result) * 1024L;\n"
          "  // deno-ibmi : sysconf(_SC_AIX_REALMEM) échoue sous PASE\n"
          "  return static_cast<int64_t>(getsystemcfg(SC_PHYSMEM));\n")
