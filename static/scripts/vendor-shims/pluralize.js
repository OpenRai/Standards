export default function pluralize(word, count, inclusive) {
  const plural = count === 1 ? word : `${word}s`;
  return inclusive ? `${count} ${plural}` : plural;
}
