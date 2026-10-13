import { useEffect, useRef, useState } from "react";
import {
  Scene,
  PerspectiveCamera,
  WebGLRenderer,
  Group,
  Mesh,
  MeshStandardMaterial,
  Color,
  Euler,
  HemisphereLight,
  DirectionalLight,
  PlaneGeometry,
  ShadowMaterial,
  PCFSoftShadowMap,
  SRGBColorSpace,
  ACESFilmicToneMapping,
} from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

function setView(scene, view) {
  const { camera, controls, render } = scene;
  const distance = Math.max(1, 0.78 / camera.aspect);
  const position =
    view === "front"
      ? [1.8, 0, 0.46]
      : view === "side"
        ? [0, 1.8, 0.46]
        : [1.28, 1.05, 0.97];
  controls.target.set(0, 0, 0.38);
  camera.position.set(
    position[0] * distance,
    position[1] * distance,
    0.38 + (position[2] - 0.38) * distance,
  );
  controls.update();
  render();
}

export default function RobotScene({ view, wireframe, reset }) {
  const mount = useRef(null);
  const sceneRef = useRef(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    const host = mount.current;
    const abort = new AbortController();
    let renderer;
    let controls;
    let resize;
    let observer;
    let visible = true;
    let ready = false;
    const geometries = new Set();
    const materials = new Set();
    const robotMaterials = [];

    async function setup() {
      try {
        renderer = new WebGLRenderer({ alpha: true, antialias: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setClearColor(0x000000, 0);
        renderer.outputColorSpace = SRGBColorSpace;
        renderer.toneMapping = ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.15;
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = PCFSoftShadowMap;
        renderer.domElement.setAttribute(
          "aria-label",
          "Interactive R08 robot model. Use the adjacent buttons for front, side and 3D views.",
        );
        renderer.domElement.setAttribute("role", "img");
        host.appendChild(renderer.domElement);
        const scene = new Scene();
        const camera = new PerspectiveCamera(34, 1, 0.01, 20);
        camera.up.set(0, 0, 1);
        controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = false;
        controls.enablePan = false;
        controls.minDistance = 0.85;
        controls.maxDistance = 3.8;
        controls.maxPolarAngle = Math.PI / 2;
        controls.rotateSpeed = 0.65;
        const render = () => {
          if (!abort.signal.aborted && visible) renderer.render(scene, camera);
        };
        controls.addEventListener("change", render);
        scene.add(new HemisphereLight(0xffffff, 0x8c9a7c, 2.7));
        const key = new DirectionalLight(0xfff4df, 4.2);
        key.position.set(2, 1, 3);
        key.castShadow = true;
        key.shadow.mapSize.set(1024, 1024);
        key.shadow.camera.left = key.shadow.camera.bottom = -1;
        key.shadow.camera.right = key.shadow.camera.top = 1;
        key.shadow.normalBias = 0.005;
        scene.add(key);
        const fill = new DirectionalLight(0xd9ebff, 2.1);
        fill.position.set(-1, -2, 1.4);
        scene.add(fill);
        const floorGeometry = new PlaneGeometry(8, 8);
        const floorMaterial = new ShadowMaterial({ opacity: 0.13 });
        geometries.add(floorGeometry);
        materials.add(floorMaterial);
        const floor = new Mesh(floorGeometry, floorMaterial);
        floor.position.z = -0.003;
        floor.receiveShadow = true;
        scene.add(floor);
        sceneRef.current = { camera, controls, render, robotMaterials };
        resize = new ResizeObserver(() => {
          if (!host.clientWidth || !host.clientHeight) return;
          camera.aspect = host.clientWidth / host.clientHeight;
          camera.updateProjectionMatrix();
          renderer.setSize(host.clientWidth, host.clientHeight);
          if (!ready) setView(sceneRef.current, "perspective");
          render();
        });
        resize.observe(host);
        observer = new IntersectionObserver(([entry]) => {
          visible = entry.isIntersecting;
          if (visible) render();
        });
        observer.observe(host);
        const response = await fetch("/model/robot.json", {
          signal: abort.signal,
        });
        if (!response.ok) throw new Error("Model unavailable");
        const data = await response.json();
        if (abort.signal.aborted) return;
        const loader = new STLLoader();
        const meshGeometries = Object.fromEntries(
          Object.entries(data.meshes).map(([name, base64]) => {
            const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
            const geometry = loader.parse(bytes.buffer);
            geometries.add(geometry);
            return [name, geometry];
          }),
        );
        const links = Object.fromEntries(
          data.links.map((name) => [name, new Group()]),
        );
        for (const joint of data.joints) {
          const child = links[joint.child];
          child.position.fromArray(joint.xyz);
          child.quaternion.setFromEuler(new Euler(...joint.rpy, "ZYX"));
          links[joint.parent].add(child);
        }
        for (const visual of data.visuals) {
          const [r, g, b, a] = visual.color;
          const material = new MeshStandardMaterial({
            color: new Color(r, g, b).convertSRGBToLinear(),
            opacity: a,
            transparent: a < 1,
            depthWrite: a === 1,
            roughness: 0.7,
            metalness: visual.mesh.includes("aluminium") ? 0.4 : 0.04,
          });
          materials.add(material);
          robotMaterials.push(material);
          const mesh = new Mesh(meshGeometries[visual.mesh], material);
          mesh.position.fromArray(visual.xyz);
          mesh.quaternion.setFromEuler(new Euler(...visual.rpy, "ZYX"));
          mesh.scale.fromArray(visual.scale);
          mesh.castShadow = a === 1;
          mesh.receiveShadow = true;
          links[visual.link].add(mesh);
        }
        const children = new Set(data.joints.map((j) => j.child));
        for (const name of data.links)
          if (!children.has(name)) scene.add(links[name]);
        ready = true;
        setView(sceneRef.current, "perspective");
        setStatus("ready");
      } catch (error) {
        if (error.name !== "AbortError" && !abort.signal.aborted)
          setStatus("error");
      }
    }
    setup();
    return () => {
      abort.abort();
      sceneRef.current = null;
      resize?.disconnect();
      observer?.disconnect();
      controls?.dispose();
      geometries.forEach((g) => g.dispose());
      materials.forEach((m) => m.dispose());
      renderer?.dispose();
      renderer?.domElement.remove();
    };
  }, []);

  useEffect(() => {
    if (sceneRef.current) setView(sceneRef.current, view);
  }, [view, reset, status]);
  useEffect(() => {
    if (!sceneRef.current) return;
    sceneRef.current.robotMaterials.forEach((material) => {
      material.wireframe = wireframe;
    });
    sceneRef.current.render();
  }, [wireframe, status]);

  return (
    <>
      <div className="three-mount" ref={mount} data-model-status={status} />
      {status === "loading" && (
        <div className="robot-fallback" role="status">
          <span>Assembling the R08 model…</span>
        </div>
      )}
      {status === "error" && (
        <div className="robot-error">
          <img
            src="/model/preview.png"
            alt="Two rendered views of the UnderBot R08 model"
          />
          <p>
            3D preview unavailable on this device.
            <br />
            <a href="/model/Underbot-R08.zip" download>
              Download the model package ↗
            </a>
          </p>
        </div>
      )}
    </>
  );
}
