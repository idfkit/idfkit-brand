# Typefaces

Both families are redistributed under the SIL Open Font License 1.1; the licence texts are beside
the files (`LICENSE-inter.txt`, `LICENSE-jetbrains-mono.txt`), as the licence requires.

| Family | Upstream release | Files taken | Weights shipped |
| ------ | ---------------- | ----------- | --------------- |
| Inter | [rsms/inter v4.1](https://github.com/rsms/inter/releases/tag/v4.1), `Inter-4.1.zip` | `extras/ttf/Inter-{Regular,Medium,SemiBold,Bold,ExtraBold}.ttf` | 400, 500, 600, 700, 800 |
| JetBrains Mono | [JetBrains/JetBrainsMono v2.304](https://github.com/JetBrains/JetBrainsMono/releases/tag/v2.304), `JetBrainsMono-2.304.zip` | `fonts/ttf/JetBrainsMono-{Regular,Medium}.ttf` | 400, 500 |

## The subset

Each file is subset to Latin with fonttools 4.62 (`pyftsubset`), keeping every layout feature, with
this unicode range:

```text
U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329,
U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD
```

The command, run from the directory the upstream archives were extracted into, for one file:

```bash
pyftsubset extras/ttf/Inter-Regular.ttf --unicodes="<the range above>" \
  --flavor=woff2 --layout-features='*' --output-file=inter-400.woff2
```

The woff2 files are what every touchpoint vendors (`dist/css/fonts/`, about 270 KB in all). The
`build/` directory holds the same subsets as TTF: `build.py` points fontconfig at them so that
`rsvg-convert` can set the property name and the repository sentence in the social images on any
host, whether or not the families are installed there. No touchpoint vendors `build/`.
