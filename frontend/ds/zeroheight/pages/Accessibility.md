# Accessibility

Alexandria Magazine está comprometido con **WCAG 2.1 Level AA** en toda la interfaz de producto y en la capa de lectura editorial. La accesibilidad no es un apartado separado del diseño — es un valor fundacional integrado en los tokens, los patrones y el sistema tipográfico.

---

## Nuestro compromiso

Una plataforma para investigadores y científicos debe ser utilizable por cualquier persona, independientemente de cómo interactúa con la tecnología. Eso incluye usuarios que navegan con teclado, utilizan lectores de pantalla, tienen visión reducida, o prefieren movimiento reducido.

**El sistema garantiza por defecto:**
- Tokens de color con contraste AA verificado en sus pares documentados
- Focus ring visible (3px azul) en todos los controles interactivos
- Estado nunca comunicado solo con color — siempre + texto + icono Lucide
- Tipografía en rem que escala sin ruptura al 200% de zoom
- Animaciones que respetan `prefers-reduced-motion`
- Vocabulario semántico correcto (ARIA roles, live regions, labels)

---

## Tres áreas de enfoque

### Normas y criterios
Los criterios WCAG 2.1 AA que aplican a Alexandria, con los valores concretos de ratio de contraste, tamaño de target, y requisitos de semántica. → Ver **Accessibility Standards**.

### Diseño accesible
Cómo aplicar el sistema de tokens para que los componentes sean accesibles por construcción, sin trabajo extra. → Ver **Designing for Accessibility**.

### Testing
Herramientas y checklist para verificar accesibilidad antes de cada release. → Ver **Testing Accessibility**.

---

## Principio clave: accesible por defecto

La accesibilidad no debe ser un post-proceso. Si construyes con los tokens semánticos (`--bg-surface`, `--text-body`, `--brand`), con los patrones documentados (labels en inputs, error text + icon, toast con aria-live), y con los componentes del sistema, estás cumpliendo WCAG 2.1 AA sin esfuerzo adicional.

Las violaciones de accesibilidad en Alexandria casi siempre provienen de:
1. No usar los tokens semánticos (hardcodear colores con mal contraste)
2. Crear controles custom sin los atributos ARIA correctos
3. Omitir labels en inputs
4. Suprimir el focus ring

Estos errores se evitan siguiendo las guías de este sistema.
