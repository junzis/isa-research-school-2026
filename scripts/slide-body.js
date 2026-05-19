<script>
document.addEventListener("DOMContentLoaded", () => {
  const sections = [
    { id: "open-flight-data", label: "Data" },
    { id: "from-trajectories-to-emissions", label: "Performance" },
    { id: "contrails-and-weather", label: "Contrail" },
    { id: "climate-optimal-routing", label: "Optimization" },
  ];

  const reveal = document.querySelector(".reveal");
  const breadcrumb = document.createElement("nav");
  breadcrumb.className = "isa-breadcrumb";
  breadcrumb.setAttribute("aria-label", "Lecture section");

  for (const section of sections) {
    const item = document.createElement("span");
    item.className = "isa-breadcrumb-item";
    item.dataset.sectionId = section.id;
    item.textContent = section.label;
    breadcrumb.appendChild(item);
  }

  reveal.appendChild(breadcrumb);

  const updateBreadcrumb = () => {
    const current = Reveal.getCurrentSlide();
    const stack = current?.parentElement?.matches(".reveal .slides > section")
      ? current.parentElement
      : null;
    const ids = [current?.id, stack?.querySelector(":scope > section.title-slide")?.id];
    const active = sections.find((section) => ids.includes(section.id));

    breadcrumb.classList.toggle("inactive", !active);
    for (const item of breadcrumb.querySelectorAll(".isa-breadcrumb-item")) {
      item.classList.toggle("active", item.dataset.sectionId === active?.id);
    }
  };

  if (window.Reveal) {
    Reveal.on("ready", updateBreadcrumb);
    Reveal.on("slidechanged", updateBreadcrumb);
    updateBreadcrumb();
  }

  for (const slide of document.querySelectorAll(".reveal .slides section.level2.regular, .reveal .slides section.level2.code")) {
    if (slide.querySelector(":scope > .slide-body")) continue;

    const heading = slide.querySelector(":scope > h2");
    if (!heading) continue;

    const body = document.createElement("div");
    body.className = "slide-body";

    for (const child of [...slide.children]) {
      if (child === heading || child.matches("aside.notes")) continue;
      body.appendChild(child);
    }

    heading.after(body);
  }
});
</script>
