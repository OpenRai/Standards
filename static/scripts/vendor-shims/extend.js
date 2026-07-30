const hasOwn = Object.prototype.hasOwnProperty;
const toString = Object.prototype.toString;
const getOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;

function isArray(value) {
  return Array.isArray(value) || toString.call(value) === "[object Array]";
}

function isPlainObject(value) {
  if (!value || toString.call(value) !== "[object Object]") {
    return false;
  }

  const hasOwnConstructor = hasOwn.call(value, "constructor");
  const hasIsPrototypeOf = value.constructor
    && value.constructor.prototype
    && hasOwn.call(value.constructor.prototype, "isPrototypeOf");
  if (value.constructor && !hasOwnConstructor && !hasIsPrototypeOf) {
    return false;
  }

  let key;
  for (key in value) {
    // Intentionally empty; mirrors extend's own-enumeration check.
  }
  return typeof key === "undefined" || hasOwn.call(value, key);
}

function getProperty(value, name) {
  if (name === "__proto__") {
    if (!hasOwn.call(value, name)) {
      return undefined;
    }
    if (getOwnPropertyDescriptor) {
      return getOwnPropertyDescriptor(value, name).value;
    }
  }
  return value[name];
}

function setProperty(target, name, value) {
  if (Object.defineProperty && name === "__proto__") {
    Object.defineProperty(target, name, {
      configurable: true,
      enumerable: true,
      value,
      writable: true
    });
    return;
  }
  target[name] = value;
}

export default function extend(...args) {
  let target = args[0];
  let index = 1;
  let deep = false;

  if (typeof target === "boolean") {
    deep = target;
    target = args[1] || {};
    index = 2;
  }

  if (target == null || (typeof target !== "object" && typeof target !== "function")) {
    target = {};
  }

  for (; index < args.length; index += 1) {
    const options = args[index];
    if (options == null) {
      continue;
    }

    for (const name in options) {
      const source = getProperty(target, name);
      const copy = getProperty(options, name);
      if (target === copy || typeof copy === "undefined") {
        continue;
      }

      if (deep && copy && (isPlainObject(copy) || isArray(copy))) {
        const clone = isArray(copy)
          ? (source && isArray(source) ? source : [])
          : (source && isPlainObject(source) ? source : {});
        setProperty(target, name, extend(true, clone, copy));
      } else {
        setProperty(target, name, copy);
      }
    }
  }

  return target;
}
