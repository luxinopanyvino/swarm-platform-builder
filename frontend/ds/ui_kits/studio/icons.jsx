/* global React */
// Icon — renders Lucide icons from the UMD `lucide.icons` registry.
// Lucide is the product's icon system (lucide-react). Names are PascalCase.
(function () {
  const cache = {};
  function camel(attrs) {
    const out = {};
    for (const k in attrs) {
      const ck = k.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      out[ck] = attrs[k];
    }
    return out;
  }
  function Icon({ name, size = 16, strokeWidth = 2, style, className }) {
    const reg = (window.lucide && window.lucide.icons) || {};
    const node = reg[name];
    if (!node) {
      // graceful fallback: empty box so layout never breaks
      return React.createElement('svg', { width: size, height: size, viewBox: '0 0 24 24' });
    }
    const children = node.map((entry, i) => {
      const [tag, attrs] = entry;
      return React.createElement(tag, Object.assign({ key: i }, camel(attrs)));
    });
    return React.createElement('svg', {
      width: size, height: size, viewBox: '0 0 24 24',
      fill: 'none', stroke: 'currentColor', strokeWidth,
      strokeLinecap: 'round', strokeLinejoin: 'round',
      style, className,
    }, children);
  }
  window.Icon = Icon;
})();
