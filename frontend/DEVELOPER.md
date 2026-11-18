# SEED Angular Developer Guide

This document provides coding conventions and best practices for the SEED Angular app, which is built using **Angular v22**, **TypeScript 6.0**, **RxJS**, and **TailwindCSS**.

Following these guidelines helps keep the codebase clean, maintainable, and scalable.

---

## Table of Contents
1. [References](#1-references)
2. [Project Philosophy](#2-project-philosophy)
3. [Angular Conventions](#3-angular-conventions)
4. [TypeScript Conventions](#4-typescript-conventions)
5. [RxJS Best Practices](#5-rxjs-best-practices)
6. [CSS & Tailwind Conventions](#6-css--tailwind-conventions)
7. [Code Organization & Structure](#7-code-organization--structure)
8. [General Best Practices](#8-general-best-practices)
9. [ESLint & Code Quality](#9-eslint--code-quality)

---

## 1. References

- **Angular Style Guide**
  [https://angular.dev/style-guide](https://angular.dev/style-guide)

- **Google TypeScript Style Guide**
  [https://google.github.io/styleguide/tsguide.html](https://google.github.io/styleguide/tsguide.html)

---

## 2. Project Philosophy

1. **Modular Code**
   - Keep functionality separated and organized into logical modules and lazy-loaded chunks.
   - Avoid monolithic, overly large files.
   - Write standalone, reusable components whenever possible.

2. **Type-Safety First**
   - Never use `any`.
   - Always prefer explicit types for parameters, return values, etc.

3. **Responsive & Modern**
   - Use **TailwindCSS** for styling, following a mobile-first approach.
   - Design components to support both light and dark themes.

4. **Maintainability & Scalability**
   - Write code that is easy to reason about and test.
   - Avoid global SCSS rules that can lead to unexpected cascading effects.

5. **Minimal External Dependencies**
   - Do not use `lodash` or other large libraries that increase bundle size unnecessarily.
   - Use built-in language features and standard RxJS operators.

---

## 3. Angular Conventions

1. **File & Folder Structure**
   - Separate logic into distinct modules (e.g., `feature` modules, `shared` modules, etc.).
   - Keep HTML, SCSS, and TS in separate files unless there is a strong reason to inline them (e.g., a single inline style: `:host { @apply flex }`).

2. **Component Templates**
   - Use `<ng-template>` for reusable snippets.
   - Follow Angular's official style guide for naming conventions (`kebab-case` file names, `UpperCamelCase` component classes, etc.).

3. **Services & Dependency Injection**
   - Leverage service classes for business logic.
   - Use a pattern of services with **private `BehaviorSubject`** and **public `Observable`** streams.
   - Prefer to pass typed objects into methods rather than multiple parameters.

4. **Lifecycle Hooks**
   - Always unsubscribe from observables in `ngOnDestroy()` to prevent memory leaks.
     - The exception to this rule is that you do not need to unsubscribe from Angular HttpClient requests - these requests emit a single value and _complete_ (automatic cleanup), so manually unsubscribing is unnecessary.

5. **Routing & Lazy Loading**
   - Take advantage of Angular's lazy-loading capabilities for modules to optimize performance.
   - Organize routes by feature or domain-specific modules.

---

## 4. TypeScript Conventions

1. **No `any`**
   - Avoid using `any` at all costs—favor explicit types or generics.
   - Ensure strong typing for parameters, return values, and variables.

2. **Types vs. Interfaces**
   - Use **types** instead of **interfaces** for consistency, unless there's a specific reason an interface is better.

3. **Variable Declarations**
   - Strive for **immutability**. Use `const` whenever possible.
   - Use `let` sparingly (only when reassignments are truly necessary).
   - Avoid unnecessary mutable state.

4. **Class Members**
   - Prefix **private** class variables with an underscore (e.g., `_myService`).
   - Use the `private` access level as much as possible - if the variable is used in the component html then use `public` or `protected`. If using `public` it isn't necessary to explicitly add the `public` keyword.

5. **Functions & Methods**
   - Do not create functions with too many arguments; pass typed objects or create dedicated configuration objects.
   - Prefer short, single-purpose functions for clarity and testability.

---

## 5. RxJS Best Practices

1. **Observables > Promises**
   - Whenever possible, use RxJS Observables instead of Promises.
   - Favor a reactive approach.

2. **Naming Conventions**
   - Append a `$` suffix to variables that hold an `Observable` (e.g., `myData$`).
   - Use standard RxJS operators rather than external libraries.

3. **Unsubscription**
   - Always unsubscribe from Observables in `ngOnDestroy()` or via `takeUntil`, `AsyncPipe`, or other safe subscription patterns to prevent leaks.

4. **BehaviorSubjects & Streams**
   - Use **private `BehaviorSubject`** for internal state management and expose it as a **public `Observable`** for read operations.

---

## 6. CSS & Tailwind Conventions

1. **Tailwind & Mobile-First**
   - Use Tailwind's utility-first classes and mobile-first approach for styling.
   - Avoid extensive global SCSS that can override or conflict with Tailwind utility classes.

2. **Themes**
   - Consider both **light** and **dark** modes in your components and styling.
   - Use Tailwind's design tokens or custom variables for theme management.

3. **Scoped Styles**
   - Scope styles to components as much as possible.
   - Inline styles are allowed if they're truly minimal and improve readability.

---

## 7. Code Organization & Structure

1. **Modular Approach**
   - Group related services, components, and models within feature or domain modules.
   - Use `index.ts` files to re-export modules and simplify imports when it makes sense.

2. **Reusable Components**
   - Strive for **standalone** and **reusable** components that can be easily shared or moved.
   - Abstract common UI patterns into shared modules/components.

3. **File Naming**
   - Use clear, consistent naming conventions (`kebab-case` for file names, `PascalCase` for class names).
   - Append `.component.ts` / `.service.ts` / `.types.ts` for clarity.

---

## 8. General Best Practices

1. **No Local Storage for User Data**
   - Avoid `localStorage` or similar in-browser storage for user-related settings.
   - Rely on backend APIs or secure storage methods.

2. **Avoid Variable Mutation**
   - Keep data structures immutable wherever possible.
   - Use spread operators and other immutable patterns instead of in-place mutations.

3. **Graphics & Media**
   - Prefer `webp` or `svg` for images to reduce file sizes and maintain quality.

4. **TODO Comments**
   - Use `// TODO:` comments to track incomplete work or future enhancements.
   - Prefer creating an issue or task in the project management tool for larger items.

5. **Clean Code Principles**
   - Write readable, self-documenting code.
   - Avoid repeating logic—extract functions or components for reuse.

6. **Translations**
   - Add translations for all text that appears in the interface

---

## 9. ESLint & Code Quality

- **ESLint**
  - Run ESLint frequently (ideally, before committing).
  - Enable ESLint in your IDE to catch problems early.
  - Fix lint errors promptly—do not commit code with lint issues.

- **Documentation**
  - Use JSDoc comment styles for public methods and classes, especially for complex logic.
