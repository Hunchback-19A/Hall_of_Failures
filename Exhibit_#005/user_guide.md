# Ranvier

**A small language for talking carefully about brains.**

The name is from the **node of Ranvier**: a gap in the myelin along a neuron’s axon, where the electrical signal is renewed rather than assumed. The editor is still **Axon**.

Version 0.1.0 (Aug 20 2026, 16:23:15)

> Never compile a destiny when you only measured a state.

This page is a tutorial. You do not need to be a programmer or a neuroscientist. If you can read a recipe, you can read Ranvier.

Python’s own tutorial starts by saying that the best way to learn is to try things. Ranvier is the same. Open a `.cog` file, press Run, and see what the compiler allows.

---

## Contents

1. [What is Ranvier?](#1-what-is-ranvier)
2. [Five minutes to your first program](#2-five-minutes-to-your-first-program)
3. [The one idea you need](#3-the-one-idea-you-need)
4. [Labels (Ranvier’s “types”)](#4-labels-ranviers-types)
5. [The language, line by line](#5-the-language-line-by-line)
6. [What the compiler will refuse](#6-what-the-compiler-will-refuse)
7. [Axon, the editor](#7-axon-the-editor)
8. [Running from the command line](#8-running-from-the-command-line)
9. [A worked example: `infant.cog`](#9-a-worked-example-infantcog)
10. [If you already program](#10-if-you-already-program)
11. [A short FAQ](#11-a-short-faq)
12. [Files in this folder](#12-files-in-this-folder)
13. [What this is not](#13-what-this-is-not)
14. [Attributions](#attributions)
15. [References](#references)

---

## 1. What is Ranvier?

Ranvier is a **fictional programming language** (file ending `.cog`) for writing *models of brain-related information*. It is named for the node of Ranvier on a neuron’s axon — a place where a signal is renewed, not taken for granted.

It is a prototype, written in Python. It is **not**:

- a real brain
- a way to upload skills
- a medical test
- a claim that consciousness has been reproduced

Think of it as a very strict notebook. You may write down anatomy, networks, measurements, and guesses about the future. You may **not** quietly turn a guess into someone’s identity.

Ordinary languages stop mistakes like:

```python
"text" + 5
```

Ranvier stops mistakes like:

```cog
FUNCTION creativity = frontal_lobe
ID person = struggling_today
DESTINY = success_probability
```

In English: *a brain region is not a talent, a bad day is not a person, and a forecast is not a fate.*

---

## 2. Five minutes to your first program

You need **Python 3.10 or newer**. Nothing else to install.

1. Open a terminal in this project folder.
2. Start the editor, **Axon**:

```bash
python -m axon
```

3. You should see a welcome that looks a little like Python’s:

```
# Welcome to Ranvier v0.1.0 (Aug 20 2026, 16:23:15)
# Begin by describing, not assuming.
# Type Help > About Axon for more information.
```

4. Press **F5** (or click **Run**).
5. In the Megaron (Output) panel you should see something like:

```
Simulation completed.
No biological interface detected.
0 prophecies compiled.
```

That last line is a joke with a serious point: Ranvier compiled a *model*, not a destiny.

To try a finished example instead:

```bash
python -m axon examples/infant.cog
```

Or without the editor:

```bash
python -m ranvier examples/infant.cog
```

---

## 3. The one idea you need

Python cares what *kind of data* you have (`str` versus `int`).

Ranvier cares what *kind of claim* you are making.

| Everyday thing | Ranvier label | Allowed to become… |
|----------------|-----------------|--------------------|
| A place on a map of the brain | `REGION` | still a place, never a talent |
| Several places working together | `NETWORK` | a home for a function |
| A skill or process (memory, language) | `FUNCTION` | associated with a network, not a lobe |
| Something true *right now* | `STATE` or `TEMP` | a later pattern or prediction — not an identity |
| A trend you have seen more than once | `PATTERN` | the basis of a prediction |
| A guess about later | `PREDICTION` | stays a guess |
| A person-code in a lab notebook | `ID` | almost nothing else |

If you remember only one rule:

**Describe first. Do not assume.**  
Name the anatomy as anatomy. Name the measurement as a measurement. Leave the person alone.

---

## 4. Labels (Ranvier’s “types”)

You declare a name by putting a **label** in front of it, the way you might write “City: Paris” on a form.

```cog
REGION frontal_lobe
FUNCTION memory
STATE current_alertness
```

After that, `frontal_lobe` is a region, `memory` is a function, and `current_alertness` is a state. The compiler remembers.

### Places and wiring

| Label | Plain English | Example |
|-------|---------------|---------|
| `REGION` | A named part of anatomy | `frontal_lobe`, `hippocampus` |
| `STRUCTURE` | Anatomy in general | `cerebrum` |
| `NETWORK` | Several regions considered together | `language_network` |
| `TRACT` | A white-matter pathway | `arcuate_fasciculus` |
| `CONNECTION` | A relationship between regions | created by `connect` |

### What the mind is *doing* (as a model, not as magic)

| Label | Plain English | Example |
|-------|---------------|---------|
| `FUNCTION` | A capability you are modeling | `language`, `attention`, `decision_making` |
| `PROCESS` | Something unfolding over time | `myelination` |
| `SIGNAL` | A simulated activity pattern | `bold_proxy` |

A function is **never** equal to one region. Language is not “the frontal lobe.” It is a network process.

### Time, not character

| Label | Plain English | Example |
|-------|---------------|---------|
| `TEMP` | Temporary | `currently_learning` |
| `STATE` | Measured at a moment | `current_alertness` |
| `PATTERN` | Repeated observation | `looking_preference` |
| `PREDICTION` | A possible future | `language_readiness` |
| `ID` | A lab code for a subject | `subject_001` |

`ID` is allowed, but it is fenced off. You may write `ID subject_001`. You may not write `ID person = failure`.

Words Ranvier will not compile as labels: `PERSONALITY`, `DESTINY`, `FATE`. It recognizes them only so it can say no.

---

## 5. The language, line by line

Each line is one thought. `#` starts a comment. The rest of that line is for humans.

### Load models

Before you use atlas names, load the notebooks the language ships with:

```cog
load atlas
load connectivity
load function
load behavior
```

| Command | What it brings in |
|---------|-------------------|
| `load atlas` | Physical regions (`brain_atlas.json`) |
| `load connectivity` | Tracts and networks (`brain_connectivity.json`) |
| `load function` | Modeled functions (`brain_function.json`) |
| `load behavior` | Observed outcomes (`brain_behavior.json`) |

These four files are kept **apart on purpose**: shape, wiring, capability, and behavior are not the same kind of fact.

### Declare a name

```cog
REGION hippocampus
NETWORK memory_network
FUNCTION memory
```

### Associate a function with a network

This is the legal way to relate “what it does” to “where a model puts it.”

```cog
associate memory with memory_network
```

Not:

```cog
FUNCTION memory = hippocampus
```

### Connect two regions with a tract

```cog
connect frontal_lobe to temporal_lobe via arcuate_fasciculus
```

### Measure a state of something anatomical or networked

```cog
measure current_alertness of attention_network
```

A measurement stays a measurement.

### Observe a behavior as a state or pattern

```cog
observe infant_looking as looking_preference
```

Looking is what you *saw*. It is not the child’s identity, and it is not the language network itself.

### Predict from a pattern or state

```cog
predict language_readiness from looking_preference
```

The result is still a `PREDICTION`. It does not become `ID` or `DESTINY`.

### Look up coordinates

```cog
lookup frontal_lobe
lookup hippocampus["centroid"]
```

If the landmark does not exist, Ranvier says so. It will not invent a place.

### Assignment (use sparingly)

```cog
STATE now = current_alertness
```

Assignment is only allowed between compatible labels. `FUNCTION` cannot take a `REGION`. `ID` cannot take a `STATE` or a `PREDICTION`.

---

## 6. What the compiler will refuse

Ranvier would rather annoy you than let a bad idea look official.

| You wrote… | The compiler hears… | Error |
|------------|---------------------|--------|
| `FUNCTION creativity = frontal_lobe` | A place is a talent | `LabelError` |
| `ID person = struggling_today` | A mood is a person | `LabelError` |
| `DESTINY = success_probability` | A forecast is fate | `ProphecyError` |
| `PERSONALITY extraversion = cerebrum` | Anatomy is character | `LabelError` |
| `lookup frontal_lobe["fake_location"]` | A place that is not on the map | `CoordinateError` |
| `observe choice as entire_cause` | One action explains everything | `AttributionError` |

Messages try to help, in the same spirit as Python’s “Did you mean…?”:

```
LabelError
Invalid semantic assignment.

FUNCTION cannot directly equal REGION.

Suggested:
associate function with network model.
```

```
ProphecyError
Prediction cannot become identity.
```

Two colors of trouble in Axon:

- **Charcoal** — the *idea* needs another look (`LabelError`, `ProphecyError`, `AttributionError`).
- **Orange** — the *tool* needs attention (a missing file, a missing model).

Nothing shouts unless the program truly cannot continue.

Try the gallery of refusals:

```bash
python -m ranvier examples/examples_of_errors.cog
```

---

## 7. Axon, the editor

Axon is a small desktop notebook for `.cog` files. It is an **IDE**, not a brain interface.

```bash
python -m axon
python -m axon examples/infant.cog
```

It uses only Python’s built-in `tkinter`. No extra packages.

| Panel | What it is for |
|-------|----------------|
| **Project** | Your `.cog` programs, the four brain model files, and saved reports |
| **Antechamber (Editor)** | Where you write. Line numbers and keyword highlighting |
| **Pillar Crypts (Models)** | Which notebooks this program loaded, and `function -> network` links |
| **Megaron (Output)** | The simulation report, or a clear error |

Tips:

- **F5** or **Run** saves, compiles, and runs.
- **Hide** on a tablet, or **View** (Ctrl+1 … Ctrl+4), shows or hides panels.
- Double-click a program in Project to open it. Click a model file to inspect it.
- Successful runs are stored under `reports/`.
- The bottom-right line reminds you: *IDE, not brain interface* / *Modeling minds, not controlling them.*

A new unsaved page is called `blank_slate.cog`.

---

## 8. Running from the command line

From this folder:

```bash
python -m ranvier examples/infant.cog
python -m ranvier examples/infant.cog --check
python -m ranvier examples/examples_of_errors.cog
python -m axon
```

`--check` validates without running the interpreter.

Exit codes: `0` means the program was accepted; `1` means Ranvier refused to compile a bad assumption.

---

## 9. A worked example: `infant.cog`

Open `examples/infant.cog`. In short, it does this:

1. Loads the four model notebooks.
2. Gives the subject a lab code: `ID subject_001` — a code, not a verdict.
3. Names anatomy as `REGION` / `STRUCTURE`.
4. Names pathways as `TRACT`.
5. Names capabilities as `FUNCTION` on `NETWORK`s.
6. Records learning as `TEMP` and `PROCESS`, not as personality.
7. Observes looking as a `PATTERN`.
8. Offers `language_readiness` only as a `PREDICTION`.

It never says the infant *is* a score. That is the whole lesson.

Educational framing for this example draws on Carter et al. (2019), “The Infant Brain.” Mesh bounds come from Dilmen’s MRI-derived models (see [References](#references)). The program still does not simulate a baby.

---

## 10. If you already program

A pocket map.

| Python | Ranvier |
|--------|-----------|
| `int`, `str`, `list` | `REGION`, `FUNCTION`, `STATE`, … |
| TypeError: `"a" + 5` | LabelError: `FUNCTION = REGION` |
| `mypy` / a compiler | `python -m ranvier file.cog` |
| IDLE | Axon (`python -m axon`) |
| `# comment` | `# comment` |
| One statement per idea | One statement per line |

There are no loops, functions, or classes. Ranvier is not a general-purpose language. It is a **safety layer** in front of a brain-related model:

```
your intention  →  Ranvier  →  computer model  →  labelled representation
```

Compatible assignments are few (for example `TEMP` with `STATE`). Almost everything else must use `associate`, `connect`, `measure`, `observe`, or `predict`.

---

## 11. A short FAQ

**Why is it called Ranvier?**  
After the **node of Ranvier** — the gaps in myelin along a neuron’s axon, where the signal is renewed. The editor is Axon.

**Do I need to know Python?**  
No. Axon is enough. Python is only how this prototype is built.

**Can this read my mind / control a brain?**  
No. Output will say *No biological interface detected.* That is by design.

**Why won’t it let me write `creativity = frontal_lobe`?**  
Because that sentence treats a map as a talent. Associate `creativity` with a *network* if you are modeling it at all.

**Why four JSON files instead of one “brain.json”?**  
So structure, wiring, function, and behavior cannot be mixed by accident.

**Are the coordinates a real MRI atlas?**  
No. They are educational boxes on published 3D meshes. See [Attributions](#attributions).

**What should I put in `ID`?**  
A subject code such as `subject_001`. Not `genius`, `failure`, or `destiny`.

---

## 12. Files in this folder

```
this folder/
├── ranvier/       the language (parser, compiler, labels, errors)
├── axon/          Axon, the editor
├── models/        atlas, connectivity, function, behavior
├── examples/      infant.cog, examples_of_errors.cog
├── reports/       simulation reports written by Axon
├── References/    source meshes and The Brain Book
├── NAMING.md      old names → new packages and commands
└── README.md      this tutorial
```

The four models:

1. **Atlas** — physical structure (Dilmen, 2015, 2016b)
2. **Connectivity** — pathways and networks (Dilmen, 2016a; tract names after Carter et al., 2019)
3. **Function** — network processes, never one-to-one with a region (Carter et al., 2019)
4. **Behavior** — observed outcomes, kept apart from mechanism (Carter et al., 2019)

---

## 13. What this is not

- Not a claim that brains can be programmed
- Not a clinical tool and not a diagnostic
- Not a one-to-one map from MRI voxels to thoughts
- Not a spaceship console, and not an oracle

The 3D files in `References/` are **meshes** (shape). Ranvier treats them as structure. It will not promote a mesh, a score, or a forecast into a person.

Ranvier began from a speculative question: if people ever needed to write down brain-related information in a program, what would a *responsible* language forbid?

It borrows Python’s readable syntax and helpful errors, a taste of structured scientific data, and a simple philosophical split: **measurement is not interpretation.**

The main feature is not simulating a brain.  
The main feature is preventing invalid assumptions about brains.

---

## Attributions

**The Brain Book.** Educational neuroscience in this prototype (lobes, networks, language pathways, memory, development, and the infant example) is adapted from Carter, Aldridge, Page, and Parker (2019), with consultants Professor Chris Frith and Professor Uta Frith. *The Brain Book* remains copyright Dorling Kindersley Limited. Ranvier does not reproduce the book’s text, figures, or scans.

**3D brain models.** Anatomical and white-matter meshes were created by Nevit Dilmen from MRI / diffusion-MRI data and retrieved via NIH 3D and Wikimedia Commons (Dilmen, 2015, 2016a, 2016b). Dilmen’s STL files on Wikimedia Commons are licensed under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) (attribution: © Nevit Dilmen) and the [GNU Free Documentation License 1.2+](http://www.gnu.org/copyleft/fdl.html). NIH 3D hosts the same entries for download and citation:

- [3DPX-002386](https://3d.nih.gov/entries/3DPX-002386) — atrophic human brain from MRI
- [3DPX-003145](https://3d.nih.gov/entries/3DPX-003145) — fractional anisotropy (brain MRI)
- [3DPX-003765](https://3d.nih.gov/entries/3DPX-003765) — 3D model of the brain

Wikimedia Commons file pages:

- [3DPX-002386 Atrophic Brain Nevit Dilmen.stl](https://commons.wikimedia.org/wiki/File:3DPX-002386_Atrophic_Brain_Nevit_Dilmen.stl)
- [3DPX-003145 Fractional Anisotrpy Tractography White Matter NevitDilmen.stl](https://commons.wikimedia.org/wiki/File:3DPX-003145_Fractional_Anisotrpy_Tractography_White_Matter_NevitDilmen.stl)
- [3DPX-003765 3DModel of Brain Nevit Dilmen.stl](https://commons.wikimedia.org/wiki/File:3DPX-003765_3DModel_of_Brain_Nevit_Dilmen.stl)

Ranvier uses derived bounding boxes and educational region overlays. That is an adaptation of Dilmen’s meshes, not an endorsement by Dilmen, NIH, or DK. Share-alike applies to redistributed adaptations of the CC BY-SA meshes themselves.

How the local `References/` files were used:

| Local file | Work cited | Role in Ranvier |
|------------|------------|-------------------|
| `The brain book.pdf` | Carter et al. (2019) | Educational anatomy, networks, language tracts, memory, development, infant example |
| `3DPX-003765_3DModel_of_Brain_Nevit_Dilmen.stl` | Dilmen (2016b) | Whole-brain mesh bounds for the atlas |
| `3DPX-002386_Atrophic_Brain_Nevit_Dilmen.stl` and `NIH 3DPX002386/` | Dilmen (2015) | Atrophic brain as a **structural** comparison, not an identity |
| `3DPX-003145_Fractional_Anisotrpy_Tractography_White_Matter_NevitDilmen.stl` | Dilmen (2016a) | FA white-matter mesh informing connectivity |
| `Source URLs.docx` | — | Local list of source links (not a published work) |

---

## References

APA 7th edition. In-text citations use author–date (Carter et al., 2019). Same-year Dilmen entries are 2016a and 2016b.

Carter, R., Aldridge, S., Page, M., & Parker, S. (2019). *The brain book* (3rd ed.). Dorling Kindersley.

Dilmen, N. (2015). *Brain* (3DPX-002386) [3D model]. NIH 3D. https://3d.nih.gov/entries/3DPX-002386

Dilmen, N. (2016a). *Fractional anisotropy (brain MRI)* (3DPX-003145) [3D model]. NIH 3D. https://3d.nih.gov/entries/3DPX-003145

Dilmen, N. (2016b). *3D model of the brain* (3DPX-003765) [3D model]. NIH 3D. https://3d.nih.gov/entries/3DPX-003765

National Institutes of Health. (n.d.). *NIH 3D* [Database]. https://3d.nih.gov/

*Note.* The 2019 UK printing used here is titled *The brain book* and lists consultants Professor Chris Frith and Professor Uta Frith on the title page. The same work is also issued in the United States as *The human brain book* (DK Publishing). Wikimedia Commons hosts CC BY-SA 3.0 copies of Dilmen’s STL files; see [Attributions](#attributions) for license URLs.
