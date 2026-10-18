import { lazy, Suspense, useEffect, useState } from "react";
import {
  ArrowUpRight,
  ArrowRight,
  ArrowDown,
  Box,
  Download,
  GitFork as Github,
  Menu,
  X,
  MoveUpRight,
  RotateCcw,
  Maximize2,
  Check,
  Plus,
  Minus,
  MousePointer2,
} from "lucide-react";
import "./App.css";

const RobotScene = lazy(() => import("./components/RobotScene"));
const REPO = "https://github.com/gautamsajeen/UnderBot-Personal";
const SOURCE = `${REPO}/tree/3f28a65`;
const systems = [
  {
    name: "Mobile base",
    tag: "01 / LOCOMOTION",
    title: "A familiar platform.\nA different direction.",
    text: "The design starts with a Worx Landroid M500 WR141E chassis. Two powered rear wheels and a passive swivel caster form the mobile base for the rest of the robot.",
    facts: [
      ["Base envelope", "558 × 404 × 205 mm"],
      ["Drive layout", "2 powered wheels + caster"],
      ["Geometry", "Simplified stock chassis"],
    ],
    shape: "base",
  },
  {
    name: "Dual arms",
    tag: "02 / MANIPULATION",
    title: "Two arms.\nMore to explore.",
    text: "Side-mounted arms bring manipulation into the same body as mobility. Each arm has five positioning axes and a coupled gripper, with mirrored joints represented in the URDF.",
    facts: [
      ["Per arm", "5 positioning axes + gripper"],
      ["Mounting", "Frame-mounted metal carriers"],
      ["Joint limits", "Proposed; hardware calibration pending"],
    ],
    shape: "arms",
  },
  {
    name: "Modular tower",
    tag: "03 / STRUCTURE",
    title: "Room to build.\nRoom to change.",
    text: "A 200 mm square aluminium frame brings the proposed power, compute and sensing layout together. Clear floors and a rear service panel make the internal arrangement accessible.",
    facts: [
      ["Frame & floors", "200 × 200 mm"],
      ["Covered body", "204 × 204 mm"],
      ["Vertical profiles", "4 × 20 × 20 × 500 mm"],
    ],
    shape: "tower",
  },
  {
    name: "Sensing & power",
    tag: "04 / INTEGRATION",
    title: "Making space for\nwhat comes next.",
    text: "The current model reserves space for an upright NOCO GB70, compute hardware, bare Kinect electronics and a top-mounted LiDAR. The exact sensor arrangement still needs measurement and calibration.",
    facts: [
      ["Power reservation", "Upright NOCO GB70"],
      ["Camera layout", "Provisional bare Kinect electronics"],
      ["LiDAR & compute", "Exact models to be confirmed"],
    ],
    shape: "sensors",
  },
];

function Brand() {
  return (
    <a className="brand" href="/" aria-label="UnderBot home">
      <span className="brand-symbol" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      underbot<span className="brand-period">.</span>
    </a>
  );
}

function Header({ explorer }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    function close(e) {
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);
  const prefix = explorer ? "/" : "";
  return (
    <header className="header">
      <div className="header-inner">
        <Brand />
        <button
          className="menu-toggle"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="main-navigation"
          onClick={() => setOpen(!open)}
        >
          {open ? <X /> : <Menu />}
        </button>
        <nav
          id="main-navigation"
          className={open ? "navigation is-open" : "navigation"}
          aria-label="Main navigation"
        >
          <a href={`${prefix}#project`} onClick={() => setOpen(false)}>
            The project
          </a>
          <a href={`${prefix}#hardware`} onClick={() => setOpen(false)}>
            Hardware
          </a>
          <a href={`${prefix}#demo`} onClick={() => setOpen(false)}>
            Demo
          </a>
          <a href={`${prefix}#development`} onClick={() => setOpen(false)}>
            Development
          </a>
          <a href={`${prefix}#resources`} onClick={() => setOpen(false)}>
            Resources
          </a>
        </nav>
        <a
          className="header-github"
          href={REPO}
          target="_blank"
          rel="noreferrer"
        >
          Build with us <ArrowUpRight size={16} />
        </a>
      </div>
    </header>
  );
}

function RobotFallback() {
  return (
    <div className="robot-fallback">
      <img
        src="/model/preview.png"
        alt="Two views of the R08 UnderBot robot model"
      />
      <span>Loading the 3D model…</span>
    </div>
  );
}

function Hero() {
  const [view, setView] = useState("perspective");
  const [wireframe, setWireframe] = useState(false);
  const [reset, setReset] = useState(0);
  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="hero-copy">
        <div className="eyebrow">
          <span className="status-dot" /> AN INDEPENDENT ROBOTICS PROJECT
        </div>
        <h1 id="hero-title">
          A body for
          <br />
          what comes
          <br />
          <span>next.</span>
          <span className="title-arrow" aria-hidden="true">
            ↗
          </span>
        </h1>
        <p className="hero-description">
          A general-purpose robot. A platform for possibility. We’re building
          UnderBot to explore VLA and WAM models in the physical world.
        </p>
        <div className="hero-actions">
          <a className="button button-dark" href="/explorer">
            Explore the robot <ArrowUpRight size={18} />
          </a>
          <a className="text-link" href="#project">
            Meet the project <ArrowDown size={16} />
          </a>
        </div>
        <div className="hero-footnote">
          <span className="mini-line" /> Built to learn. Designed to evolve.
        </div>
      </div>
      <div className="robot-stage">
        <div className="stage-top">
          <span>
            <span className="status-dot" /> R08 / DESIGN MODEL
          </span>
          <span className="stage-coordinate">X · Y · Z</span>
        </div>
        <div className="stage-watermark" aria-hidden="true">
          UB—08
        </div>
        <Suspense fallback={<RobotFallback />}>
          <RobotScene view={view} wireframe={wireframe} reset={reset} />
        </Suspense>
        <div className="model-label">
          <span className="crosshair">+</span>
          <div>
            UNDERBOT <span>R08</span>
            <small>Worx WR141E / dual-arm platform</small>
          </div>
        </div>
        <a
          className="expand-model"
          href="/explorer"
          aria-label="Open full model explorer"
        >
          <Maximize2 size={18} />
        </a>
        <div className="stage-bottom">
          <div className="view-switch" aria-label="Model viewpoint">
            {["perspective", "front", "side"].map((v) => (
              <button
                key={v}
                aria-pressed={view === v}
                onClick={() => setView(v)}
              >
                {v === "perspective" ? "3D view" : v}
              </button>
            ))}
          </div>
          <div className="stage-tools">
            <button
              aria-label="Toggle wireframe"
              aria-pressed={wireframe}
              onClick={() => setWireframe(!wireframe)}
            >
              <Box size={17} />
            </button>
            <button
              aria-label="Reset model view"
              onClick={() => {
                setView("perspective");
                setReset((v) => v + 1);
              }}
            >
              <RotateCcw size={17} />
            </button>
          </div>
        </div>
        <div className="orbit-hint">
          <MousePointer2 size={12} /> Drag to orbit · scroll to zoom
        </div>
      </div>
    </section>
  );
}

function Blueprint({ active }) {
  return (
    <svg
      className={`blueprint blueprint-${active}`}
      viewBox="0 0 520 420"
      role="img"
      aria-label="Schematic of the mobile base, tower, arms and sensor locations; not to scale"
    >
      <defs>
        <pattern
          id="draft-grid"
          width="24"
          height="24"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M 24 0 L 0 0 0 24"
            fill="none"
            stroke="currentColor"
            strokeWidth=".4"
            opacity=".14"
          />
        </pattern>
      </defs>
      <rect width="520" height="420" fill="url(#draft-grid)" />
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      >
        <g className="bp-part bp-base">
          <path d="M108 293 279 253 421 303 244 352Z M108 293v30l136 49 177-43v-26M244 352v20" />
          <path d="m118 290 15-29 155-32 112 40 12 30" />
          <ellipse
            cx="157"
            cy="335"
            rx="22"
            ry="31"
            transform="rotate(-18 157 335)"
          />
          <ellipse
            cx="367"
            cy="344"
            rx="22"
            ry="31"
            transform="rotate(18 367 344)"
          />
        </g>
        <g className="bp-part bp-tower">
          <path d="m212 102 86-19 63 24-87 21Z M212 102v186l62 24 87-20V107M274 128v184M298 83v182" />
          <path d="m212 154 62 24 87-20m-149 37 62 24 87-20m-149 37 62 24 87-20" />
          <path d="m222 110 0 171 44 17V128m16 7v164l70-16V117" />
        </g>
        <g className="bp-part bp-arms">
          <path d="m217 165-28 17-31 56-25-9-16 37 13 7 19-26 22 8 35-61 11-5M353 162l31 14 20 46 25-10 20 33-12 9-16-26-28 10-28-52-12-7" />
          <circle cx="198" cy="188" r="7" />
          <circle cx="164" cy="243" r="6" />
          <circle cx="376" cy="182" r="7" />
          <circle cx="400" cy="230" r="6" />
          <path d="m117 266-12 13 10 12m15-18-4 15 9 5m302-39 5 18 11 1m-4-28 16 13-1 12" />
        </g>
        <g className="bp-part bp-sensors">
          <ellipse cx="285" cy="76" rx="20" ry="7" />
          <path d="M265 76V61m40 15V61" />
          <ellipse cx="285" cy="61" rx="20" ry="7" />
          <path d="m222 142 41 15v12l-41-15Z" />
          <circle cx="232" cy="152" r="3" />
          <circle cx="252" cy="160" r="3" />
        </g>
        <g strokeWidth=".8" opacity=".6">
          <path
            d="M83 289v85m-5-2h10m-5-83h10M112 392l130 0 184-44m-314 38v12m130-12v12m184-55v12M386 85h40m-5 0v197m-5 0h10"
            strokeDasharray="3 4"
          />
        </g>
      </g>
      <g fill="currentColor" fontSize="10" fontFamily="monospace">
        <text x="102" y="411">
          558 mm BASE LENGTH
        </text>
        <text x="430" y="191" transform="rotate(90 430 191)">
          500 mm POSTS
        </text>
        <text x="24" y="28">
          UB / SYSTEM STUDY
        </text>
        <text x="24" y="397" opacity=".5">
          SCHEMATIC · NOT TO SCALE
        </text>
      </g>
      <g className="bp-marker">
        <circle
          cx={
            active === "base"
              ? 244
              : active === "arms"
                ? 162
                : active === "tower"
                  ? 274
                  : 285
          }
          cy={
            active === "base"
              ? 350
              : active === "arms"
                ? 242
                : active === "tower"
                  ? 218
                  : 61
          }
          r="5"
        />
      </g>
    </svg>
  );
}

function Hardware() {
  const [active, setActive] = useState(0);
  const system = systems[active];
  return (
    <section id="hardware" className="section hardware-section">
      <div className="section-heading">
        <div>
          <div className="eyebrow">02 / THE HARDWARE</div>
          <h2>
            One body.
            <br />
            Many moving parts.
          </h2>
        </div>
        <p>
          Repurposed foundations. Purpose-built additions.
          <br />
          Explore the systems behind the R08 design.
        </p>
      </div>
      <div
        className="hardware-tabs"
        role="tablist"
        aria-label="Robot subsystems"
      >
        {systems.map((s, i) => (
          <button
            key={s.name}
            id={`tab-${i}`}
            role="tab"
            aria-selected={active === i}
            aria-controls="system-panel"
            tabIndex={active === i ? 0 : -1}
            onClick={() => setActive(i)}
            onKeyDown={(e) => {
              let next;
              if (e.key === "ArrowRight") next = (i + 1) % systems.length;
              if (e.key === "ArrowLeft")
                next = (i + systems.length - 1) % systems.length;
              if (e.key === "Home") next = 0;
              if (e.key === "End") next = systems.length - 1;
              if (next !== undefined) {
                e.preventDefault();
                setActive(next);
                document.getElementById(`tab-${next}`).focus();
              }
            }}
          >
            <span>0{i + 1}</span>
            {s.name}
            <ArrowUpRight size={18} />
          </button>
        ))}
      </div>
      <div
        className="system-panel"
        id="system-panel"
        role="tabpanel"
        aria-labelledby={`tab-${active}`}
        tabIndex="0"
      >
        <div className="blueprint-wrap">
          <Blueprint active={system.shape} />
          <span className="blueprint-caption">
            R08 / COMPONENT ARCHITECTURE
          </span>
        </div>
        <div className="system-copy">
          <span className="eyebrow">{system.tag}</span>
          <h3>{system.title}</h3>
          <p>{system.text}</p>
          <dl>
            {system.facts.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
          <a
            href={`${SOURCE}/underbot_description/docs/accuracy_and_physics.md`}
            target="_blank"
            rel="noreferrer"
            className="text-link"
          >
            Read the engineering notes <ArrowUpRight size={16} />
          </a>
        </div>
      </div>
    </section>
  );
}

const resources = [
  {
    number: "01",
    title: "The robot model",
    description: "R08 URDF, meshes, Xacro and supporting files.",
    label: "Download package",
    href: "/model/Underbot-R08.zip",
    icon: Download,
    download: true,
  },
  {
    number: "02",
    title: "Explore in 3D",
    description: "Inspect the geometry and move individual joints.",
    label: "Open model explorer",
    href: "/explorer",
    icon: Box,
  },
  {
    number: "03",
    title: "Engineering notes",
    description: "Dimensions, assumptions and validation reports.",
    label: "Read the documentation",
    href: `${SOURCE}/underbot_description/README.md`,
    icon: ArrowUpRight,
  },
  {
    number: "04",
    title: "The source",
    description: "Follow the design and get into the details.",
    label: "View on GitHub",
    href: REPO,
    icon: Github,
  },
];

function Home() {
  return (
    <>
      <main id="main">
        <div className="container">
          <Hero />
        </div>
        <div className="spec-strip">
          <div className="container spec-grid">
            <div className="spec-intro">
              <span className="status-dot" /> THE R08 DESIGN
              <span>At a glance</span>
            </div>
            <div>
              <strong>02</strong>
              <span>Articulated arms</span>
            </div>
            <div>
              <strong>
                200<span> × </span>200<small> mm</small>
              </strong>
              <span>Tower frame · not base footprint</span>
            </div>
            <div>
              <strong>
                23<span> / </span>22
              </strong>
              <span>Links / joints in the model</span>
            </div>
            <div>
              <strong>URDF</strong>
              <span>Model + meshes available</span>
            </div>
          </div>
        </div>
        <div className="container">
          <section id="project" className="section project-section">
            <div className="eyebrow">01 / THE IDEA</div>
            <div className="project-grid">
              <h2>
                Intelligence needs
                <br />
                <span>a place to move.</span>
              </h2>
              <div className="project-copy">
                <p className="lead">
                  New models need a body to learn from. That’s where UnderBot
                  comes in.
                </p>
                <p>
                  Our goal is a general-purpose robot platform for testing VLA
                  and WAM models: a physical meeting point for perception,
                  action and experimentation.
                </p>
                <p>
                  We’re bringing mobility, two arms and a modular hardware
                  layout into one evolving design—and sharing the work so others
                  can follow, question and contribute.
                </p>
                <a className="text-link" href="#development">
                  See where we are <ArrowDown size={16} />
                </a>
              </div>
            </div>
            <div className="principles">
              <div>
                <span>01</span>
                <h3>A general-purpose body</h3>
                <p>
                  A shared platform for exploring different tasks and models.
                </p>
              </div>
              <div>
                <span>02</span>
                <h3>Made to be modified</h3>
                <p>A modular structure with room for the next experiment.</p>
              </div>
              <div>
                <span>03</span>
                <h3>Built in the open</h3>
                <p>
                  Published design files, documented assumptions and visible
                  progress.
                </p>
              </div>
            </div>
          </section>
          <Hardware />
          <section id="demo" className="section demo-section">
            <div className="section-heading">
              <div>
                <div className="eyebrow">03 / NAVIGATION IN SIMULATION</div>
                <h2>From a goal<br />to a path.</h2>
              </div>
              <p>
                The R08 model inside our navigation workflow. Watch the planned
                route and simulated robot motion in Foxglove.
              </p>
            </div>
            <figure className="demo-recording">
              <video
                controls
                playsInline
                preload="none"
                poster="/media/underbot-navigation.jpg"
                aria-label="UnderBot R08 navigation simulation"
                aria-describedby="demo-description"
                width="2560"
                height="1046"
              >
                <source src="/media/underbot-navigation.mp4" type="video/mp4" />
                <a href="/media/underbot-navigation.mp4">Download the navigation recording</a>
              </video>
              <figcaption>
                <span>FOXGLOVE / R08 MODEL</span>
                <span>1:09 · SILENT RECORDING · 13 OCT 2026</span>
              </figcaption>
            </figure>
            <div className="demo-context">
              <p id="demo-description">
                A yellow planned path crosses a 3D point-cloud map. The R08
                robot model moves along the route as the view changes from a
                map overview to a close-up of the robot. This recording shows
                our A* navigation simulation; physical navigation and VLA / WAM
                experiments are future validation steps.
              </p>
              <a className="text-link" href="/media/underbot-navigation.mp4" download>
                Download recording <Download size={16} />
              </a>
            </div>
          </section>
        </div>
        <section id="development" className="development-section">
          <div className="container">
            <div className="section-heading">
              <div>
                <div className="eyebrow">04 / WORK IN PROGRESS</div>
                <h2>
                  A real project.
                  <br />
                  An evolving robot.
                </h2>
              </div>
              <p>
                The R08 model is a foundation for the next steps.
                <br />
                Here’s what is documented, and what comes next.
              </p>
            </div>
            <div className="development-grid">
              <article className="milestone">
                <span className="milestone-status">
                  <Check size={14} /> AVAILABLE
                </span>
                <h3>The digital foundation</h3>
                <p>
                  Robot geometry, joint definitions, collision shapes and
                  inertial properties are included in the published R08 package.
                </p>
                <ul>
                  <li>URDF + modular Xacro</li>
                  <li>45 visual STL meshes</li>
                  <li>Offline joint inspector</li>
                </ul>
                <a
                  href={`${SOURCE}/underbot_description/validation/delivery_check.json`}
                  target="_blank"
                  rel="noreferrer"
                >
                  View the model report <ArrowUpRight size={16} />
                </a>
              </article>
              <article className="milestone">
                <span className="milestone-status in-progress">
                  <span className="status-dot" /> TO VERIFY ON HARDWARE
                </span>
                <h3>Closing the physical gap</h3>
                <p>
                  The model includes estimates. Real measurements will refine
                  arm geometry, installed masses, sensor placement and
                  calibration.
                </p>
                <ul>
                  <li>Joint limits and actuator effort</li>
                  <li>Camera packaging and optical frames</li>
                  <li>Installed mass and mounting details</li>
                </ul>
                <a
                  href={`${SOURCE}/underbot_description/docs/accuracy_and_physics.md`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Explore the open questions <ArrowUpRight size={16} />
                </a>
              </article>
              <article className="milestone">
                <span className="milestone-status future">
                  <MoveUpRight size={14} /> PROJECT DIRECTION
                </span>
                <h3>A body for model research</h3>
                <p>
                  The aim is to bring VLA and WAM experiments onto a
                  general-purpose mobile robot, then learn from interaction with
                  the physical world.
                </p>
                <ul>
                  <li>Connect perception and action</li>
                  <li>Explore mobile manipulation</li>
                  <li>Iterate on the shared platform</li>
                </ul>
                <a href={REPO} target="_blank" rel="noreferrer">
                  Follow the project <ArrowUpRight size={16} />
                </a>
              </article>
            </div>
            <p className="development-note">
              Model checks include MuJoCo and PyBullet reports. Native ROS /
              RViz, Gazebo and Isaac Sim execution is not confirmed by the
              source package. Hardware payload and autonomy performance have not
              been established.
            </p>
          </div>
        </section>
        <div className="container">
          <section id="resources" className="section resources-section">
            <div className="section-heading">
              <div>
                <div className="eyebrow">05 / GET INTO THE DETAILS</div>
                <h2>
                  Less mystery.
                  <br />
                  More source files.
                </h2>
              </div>
              <p>
                Start with the model, explore the mechanics,
                <br />
                or follow the engineering decisions.
              </p>
            </div>
            <div className="resource-list">
              {resources.map(
                ({
                  number,
                  title,
                  description,
                  label,
                  href,
                  icon: Icon,
                  download,
                }) => (
                  <a
                    key={number}
                    className="resource-row"
                    href={href}
                    download={download || undefined}
                    target={href.startsWith("https:") ? "_blank" : undefined}
                    rel={href.startsWith("https:") ? "noreferrer" : undefined}
                  >
                    <span className="resource-number">{number}</span>
                    <div>
                      <h3>{title}</h3>
                      <p>{description}</p>
                    </div>
                    <span className="resource-action">{label}</span>
                    <Icon size={21} />
                  </a>
                ),
              )}
            </div>
          </section>
          <section className="faq-section">
            <div>
              <div className="eyebrow">A FEW THINGS TO KNOW</div>
              <h2>
                Curious?
                <br />
                Start here.
              </h2>
            </div>
            <div className="faq-list">
              {[
                [
                  "What is UnderBot being built for?",
                  "UnderBot’s purpose is to provide a general-purpose robot body for testing new VLA and WAM models. Mobility and dual arms make it a platform for exploring how models interact with the physical world.",
                ],
                [
                  "Is the 3D model the finished physical robot?",
                  "The viewer shows the published R08 design model. Some geometry, masses and hardware limits are estimates. It is a design and experimentation resource, rather than a verified representation of a completed physical build.",
                ],
                [
                  "Can I use the files with ROS 2?",
                  "The package includes a ROS URDF, modular Xacro, RViz configuration and display launch file. It also includes a portable URDF and simulator import guidance. Native ROS and RViz execution was not verified in the source delivery; consult the package README for setup.",
                ],
                [
                  "How can I get involved?",
                  "Explore the source repository, review the engineering notes, or open a GitHub issue with a concrete question or proposed improvement. The repository has no specified license, so check with its maintainers before redistributing or reusing the design.",
                ],
              ].map(([q, a]) => (
                <details key={q}>
                  <summary>
                    {q}
                    <Plus className="faq-plus" size={18} />
                    <Minus className="faq-minus" size={18} />
                  </summary>
                  <p>{a}</p>
                </details>
              ))}
            </div>
          </section>
          <section className="join-section">
            <div className="eyebrow">THE NEXT CHAPTER IS STILL BEING BUILT</div>
            <h2>
              Let’s give ideas
              <br />a body.
            </h2>
            <div className="join-bottom">
              <p>
                Follow the experiments. Question the design.
                <br />
                Help shape what UnderBot becomes.
              </p>
              <a
                className="button button-dark"
                href={REPO}
                target="_blank"
                rel="noreferrer"
              >
                <Github size={18} /> Join us on GitHub{" "}
                <ArrowUpRight size={18} />
              </a>
            </div>
            <span className="join-arrow" aria-hidden="true">
              ↗
            </span>
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
}

function Footer() {
  return (
    <footer className="footer container">
      <div>
        <Brand />
        <p>A body for what comes next.</p>
      </div>
      <div className="footer-links">
        <a href={REPO} target="_blank" rel="noreferrer">
          Robot repository <ArrowUpRight size={13} />
        </a>
        <a
          href="https://github.com/jacobsrepo/Underbot-Website"
          target="_blank"
          rel="noreferrer"
        >
          Website source <ArrowUpRight size={13} />
        </a>
        <span>R08 design · An ongoing robotics project</span>
      </div>
    </footer>
  );
}

function Explorer() {
  return (
    <>
      <main id="main" className="explorer-page container">
        <a className="text-link" href="/">
          ← Back to the project
        </a>
        <div className="explorer-heading">
          <div>
            <div className="eyebrow">R08 / INTERACTIVE MODEL</div>
            <h1>Meet the moving parts.</h1>
          </div>
          <a
            className="button button-outline"
            href="/model/Underbot-R08.zip"
            download
          >
            Download the model <Download size={17} />
          </a>
        </div>
        <p className="explorer-intro">
          Orbit the actual geometry, move the joints and compare visual and
          collision shapes. This is a kinematic model inspector; it does not
          simulate forces or control hardware.
        </p>
        <iframe
          className="model-iframe"
          title="UnderBot R08 interactive URDF joint inspector"
          src="/model/viewer.html"
        />
        <p className="explorer-source">
          Model: R08 · 23 links · 22 joints. Some dimensions and hardware
          properties remain estimates.{" "}
          <a
            href={`${SOURCE}/underbot_description/docs/accuracy_and_physics.md`}
            target="_blank"
            rel="noreferrer"
          >
            Read the accuracy register <ArrowUpRight size={13} />
          </a>
        </p>
      </main>
      <Footer />
    </>
  );
}

function NotFound() {
  return (
    <main id="main" className="not-found container">
      <div className="eyebrow">404 / OFF THE MAP</div>
      <h1>
        Let’s head back
        <br />
        to the robot.
      </h1>
      <a className="button button-dark" href="/">
        Return home <ArrowRight size={17} />
      </a>
    </main>
  );
}

export default function App() {
  const path = window.location.pathname.replace(/\/$/, "") || "/";
  const explorer = path === "/explorer" || path === "/dashboard";
  useEffect(() => {
    document.title = explorer
      ? "Model explorer — UnderBot"
      : path === "/"
        ? "UnderBot — A body for what comes next"
        : "Page not found — UnderBot";
  }, [explorer, path]);
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <Header explorer={path !== "/"} />
      {explorer ? <Explorer /> : path === "/" ? <Home /> : <NotFound />}
    </>
  );
}
