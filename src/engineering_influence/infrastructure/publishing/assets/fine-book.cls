% fine-book.cls
% Interior design for the Adam Matthew Steinberger books.
% 6 x 9 in trade paperback, Amazon KDP print-ready (no bleed, black and grayscale only).
% Built on memoir; typeset with LuaLaTeX.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{fine-book}[2026/10/28 Fine book interior]

\LoadClass[11pt,twoside,openright]{memoir}

% ---------------------------------------------------------------------------
% Page geometry. KDP 6x9, no bleed.
% Inside (gutter) 0.875in covers every KDP page-count tier up to 828 pages.
% Outside 0.6875in, well above the 0.25in KDP minimum. Running heads and folios
% sit inside the live area.
% ---------------------------------------------------------------------------
\setstocksize{9in}{6in}
\settrimmedsize{\stockheight}{\stockwidth}{*}
\settrims{0pt}{0pt}
\setlrmarginsandblock{0.875in}{0.6875in}{*}
\setulmarginsandblock{0.85in}{0.9in}{*}
\setheadfoot{16pt}{24pt}
\setheaderspaces{*}{16pt}{*}
\checkandfixthelayout[fixed]

% ---------------------------------------------------------------------------
% Fonts and microtypography
% ---------------------------------------------------------------------------
% Every face is loaded from fonts/ beside the class (staged by BookBuilder from
% the packaged fonts/ folder), never from the TeX installation. Distributions package EB Garamond
% differently (Debian ships the initials separately), and a different font build changes
% line breaks, page counts, and so cover spine widths. Vendored fonts make local and CI
% builds identical.
\RequirePackage{fontspec}
\RequirePackage[english]{babel}
\newfontfamily\displayfont{EBGaramond}[
  Path=fonts/,
  Extension=.otf,
  UprightFont=*-Regular,
  ItalicFont=*-Italic,
  BoldFont=*-Medium,
  Numbers={Lining,Proportional},
  LetterSpace=0]
\newfontfamily\liningfont{EBGaramond}[
  Path=fonts/,
  Extension=.otf,
  UprightFont=*-Regular,
  ItalicFont=*-Italic,
  BoldFont=*-SemiBold,
  Numbers={Lining,Tabular}]
\newfontfamily\capsfont{EBGaramond}[
  Path=fonts/,
  Extension=.otf,
  UprightFont=*-Regular,
  ItalicFont=*-Italic,
  BoldFont=*-Medium,
  Letters={SmallCaps,UppercaseSmallCaps},
  Numbers={OldStyle,Proportional}]
\newfontfamily\initialsfont{EBGaramond-Initials}[Path=fonts/,Extension=.otf]

% Glyphs EB Garamond lacks (arrows, a few math symbols) fall back to Libertinus.
\directlua{
  luaotfload.add_fallback("bookfallback", {
    "[fonts/LibertinusSerif-Regular.otf]:mode=node;",
    "[fonts/DejaVuSerif.ttf]:mode=node;",
  })
}
\setmainfont{EBGaramond}[
  Path=fonts/,
  Extension=.otf,
  UprightFont=*-Regular,
  ItalicFont=*-Italic,
  BoldFont=*-SemiBold,
  BoldItalicFont=*-SemiBoldItalic,
  Numbers={OldStyle,Proportional},
  Ligatures={Common,TeX},
  Kerning=On,
  RawFeature={fallback=bookfallback}]

\RequirePackage[protrusion=true,expansion=true,tracking=true,
  final,babel=true]{microtype}
\SetTracking{encoding=*,shape=sc}{60}
\SetTracking[spacing={450,,}]{encoding=*}{150}

\RequirePackage[gray]{xcolor}        % B&W interior: every colour becomes a gray
\definecolor{ink}{gray}{0}
\definecolor{softink}{gray}{0.30}
\definecolor{rulegray}{gray}{0.55}
\definecolor{wash}{gray}{0.94}

\RequirePackage{graphicx}
\RequirePackage{calc}
\RequirePackage{needspace}
\RequirePackage{enumitem}
\RequirePackage{tabularx}
\RequirePackage{booktabs}
\RequirePackage{lettrine}
\RequirePackage{pgfornament}
\RequirePackage[most]{tcolorbox}
\RequirePackage{etoolbox}

% Body text: 11pt on 15pt.
\renewcommand{\normalsize}{\fontsize{11}{15}\selectfont}
\normalsize
\setlength{\parindent}{1.15em}
\setlength{\parskip}{0pt}
\frenchspacing
\widowpenalty=10000
\clubpenalty=10000
\displaywidowpenalty=10000
\brokenpenalty=10000
\emergencystretch=1.2em
\tolerance=600
\pretolerance=150
\raggedbottom

\setlist{itemsep=0.25\baselineskip, topsep=0.45\baselineskip, parsep=0pt,
  leftmargin=1.5em}
\setlist[itemize]{label={\textcolor{softink}{\raisebox{0.12ex}{\scriptsize\textbullet}}}}
\setlist[enumerate]{label={\liningfont\arabic*.}}

\newcommand{\ornament}[1][1.6em]{%
  {\color{softink}\pgfornament[width=#1]{15}}}
\newcommand{\smallornament}{{\color{softink}\pgfornament[width=1.1em]{94}}}

\newcommand{\spacedcaps}[1]{{\capsfont\textls[180]{#1}}}

% ---------------------------------------------------------------------------
% Running heads and folios
% ---------------------------------------------------------------------------
\newcommand{\booktitlehead}{}
\newcommand{\setbooktitlehead}[1]{\renewcommand{\booktitlehead}{#1}}
\makepagestyle{fine}
\makeevenhead{fine}{\liningfont\small\thepage}{\footnotesize\spacedcaps{\booktitlehead}}{}
\makeoddhead{fine}{}{\footnotesize\spacedcaps{\rightmark}}{\liningfont\small\thepage}
\makeevenfoot{fine}{}{}{}
\makeoddfoot{fine}{}{}{}
\makepsmarks{fine}{%
  \nouppercaseheads
  \createmark{chapter}{both}{nonumber}{}{}
  \createmark{section}{right}{nonumber}{}{}}
\makepagestyle{opener}
\makeevenfoot{opener}{}{\liningfont\small\thepage}{}
\makeoddfoot{opener}{}{\liningfont\small\thepage}{}
\aliaspagestyle{chapter}{opener}
\aliaspagestyle{part}{empty}
\aliaspagestyle{cleared}{empty}
\aliaspagestyle{afterpart}{empty}
\pagestyle{fine}

% Running heads use the short chapter title, never section titles.
\newcommand{\chapterheadmark}[1]{\markboth{#1}{#1}}

% ---------------------------------------------------------------------------
% Parts
% ---------------------------------------------------------------------------
\renewcommand{\partnamefont}{\spacedcaps}
\renewcommand{\partnumfont}{\spacedcaps}
\renewcommand{\parttitlefont}{\displayfont\fontsize{26}{32}\selectfont}
\renewcommand{\printpartname}{}
\renewcommand{\printpartnum}{%
  {\small\partnamefont{part \bookNumberWord{\value{part}}}}}
\renewcommand{\midpartskip}{\par\vskip 22pt}
\renewcommand{\printparttitle}[1]{%
  \begin{minipage}{0.86\textwidth}\centering\parttitlefont #1\end{minipage}%
  \par\vskip 26pt\ornament[2.2em]}
\renewcommand{\beforepartskip}{\null\vskip 0pt plus 0.9fil}
\renewcommand{\afterpartskip}{\vskip 0pt plus 1.1fil\newpage}

% Number words for "Part One", "Chapter Seven"
\newcommand{\bookNumberWord}[1]{%
  \ifcase#1\or one\or two\or three\or four\or five\or six\or seven\or eight\or
  nine\or ten\or eleven\or twelve\or thirteen\or fourteen\or fifteen\or
  sixteen\or seventeen\or eighteen\or nineteen\or twenty\or twenty-one\or
  twenty-two\or twenty-three\or twenty-four\or twenty-five\or twenty-six\or
  twenty-seven\or twenty-eight\or twenty-nine\or thirty\or thirty-one\or
  thirty-two\or thirty-three\or thirty-four\or thirty-five\or thirty-six\or
  thirty-seven\or thirty-eight\or thirty-nine\or forty\else\number#1\fi}

% ---------------------------------------------------------------------------
% Chapters
% ---------------------------------------------------------------------------
\makechapterstyle{fine}{%
  \setlength{\beforechapskip}{0.55in}
  \setlength{\midchapskip}{18pt}
  \setlength{\afterchapskip}{40pt}
  \renewcommand{\chapnamefont}{\spacedcaps}
  \renewcommand{\chapnumfont}{\spacedcaps}
  \renewcommand{\chaptitlefont}{\displayfont\fontsize{23}{29}\selectfont}
  \renewcommand{\printchaptername}{}
  \renewcommand{\chapternamenum}{}
  \renewcommand{\printchapternum}{\centering
    {\small\chapnamefont{chapter \bookNumberWord{\value{chapter}}}}}
  \renewcommand{\afterchapternum}{\par\nobreak\vskip\midchapskip}
  \renewcommand{\printchapternonum}{\centering\vphantom{\chapnamefont{chapter}}%
    \par\nobreak\vskip\midchapskip}
  \renewcommand{\printchaptertitle}[1]{%
    \centering\begin{minipage}{0.9\textwidth}\centering\chaptitlefont ##1\end{minipage}%
    \par\nobreak\vskip 16pt\ornament}
  \renewcommand{\afterchaptertitle}{\par\nobreak\vskip\afterchapskip}
}
\chapterstyle{fine}

% ---------------------------------------------------------------------------
% Sections (unnumbered, not in the contents)
% ---------------------------------------------------------------------------
\setsecnumdepth{chapter}
\settocdepth{chapter}
\setsecheadstyle{\displayfont\fontsize{14.5}{18}\selectfont\raggedright}
\setbeforesecskip{-1.7\baselineskip plus -0.4\baselineskip minus -0.2\baselineskip}
\setaftersecskip{0.75\baselineskip plus 0.1\baselineskip}
\setsubsecheadstyle{\displayfont\itshape\fontsize{12.5}{16}\selectfont\raggedright}
\setbeforesubsecskip{-1.25\baselineskip plus -0.3\baselineskip minus -0.1\baselineskip}
\setaftersubsecskip{0.45\baselineskip plus 0.1\baselineskip}
\setsubsubsecheadstyle{\normalfont\itshape}
\setbeforesubsubsecskip{-0.9\baselineskip plus -0.2\baselineskip}
\setaftersubsubsecskip{-0.6em}
\newcommand{\booksection}[1]{\needspace{5\baselineskip}\section*{#1}}
\newcommand{\booksubsection}[1]{\needspace{4\baselineskip}\subsection*{#1}}
\newcommand{\booksubsubsection}[1]{\needspace{3\baselineskip}\subsubsection*{#1.}}

% ---------------------------------------------------------------------------
% Drop caps
% ---------------------------------------------------------------------------
\renewcommand{\LettrineFontHook}{\displayfont}
\renewcommand{\LettrineTextFont}{\capsfont}
\setcounter{DefaultLines}{3}
\setlength{\DefaultFindent}{0.18em}
\setlength{\DefaultNindent}{0.1em}
\renewcommand{\DefaultLhang}{0.08}
\newcommand{\opening}[2]{\lettrine[lines=3,loversize=0.06]{#1}{#2}}

% ---------------------------------------------------------------------------
% Callouts: a quiet gray panel with an ornament, no heavy rules.
% ---------------------------------------------------------------------------
\newtcolorbox{callout}{%
  enhanced, breakable,
  colback=wash, colframe=wash,
  boxrule=0pt, arc=1.5pt, outer arc=1.5pt,
  left=15pt, right=15pt, top=17pt, bottom=12pt,
  before skip=1.15\baselineskip plus 2pt, after skip=1.15\baselineskip plus 2pt,
  fontupper=\fontsize{11.5}{15.5}\selectfont\itshape,
  parbox=false,
  overlay unbroken and first={%
    \node[anchor=center, fill=white, inner xsep=6pt, inner ysep=2pt]
      at ([yshift=0pt]frame.north) {\color{softink}\pgfornament[width=1.5em]{94}};},
}
\BeforeBeginEnvironment{callout}{\par\needspace{4\baselineskip}}
% Bold inside an italic callout reads as semibold italic.

% Quotations and epigraphs
\renewenvironment{quote}
  {\list{}{\leftmargin=1.6em\rightmargin=1.2em\topsep=0.55\baselineskip}%
   \item\relax\fontsize{10.5}{14.5}\selectfont}
  {\endlist}
\newenvironment{chapterepigraph}[1]
  {\def\epigraphsource{#1}\begin{flushright}\begin{minipage}{0.78\textwidth}%
   \raggedleft\itshape\fontsize{10.5}{14.5}\selectfont}
  {\par\vskip 4pt\upshape\footnotesize\spacedcaps{\epigraphsource}%
   \end{minipage}\end{flushright}\vskip 1.2\baselineskip}

% Bibliography and reference lists: hanging indent, smaller type.
\newenvironment{referencelist}
  {\par\fontsize{10}{13.5}\selectfont}
  {\par}
\newcommand{\refentry}[1]{\par{\raggedright\hangindent=1.4em\hangafter=1
  \noindent #1\par}\vskip 0.35\baselineskip plus 1pt}

% A chapter-level notice set in the same quiet panel, used for the
% "illustrative example" labels.
\newtcolorbox{illustration}[1][]{%
  enhanced, breakable,
  colback=white, colframe=rulegray, boxrule=0.5pt, arc=1.5pt,
  left=14pt, right=14pt, top=10pt, bottom=10pt,
  before skip=1.1\baselineskip, after skip=1.1\baselineskip,
  parbox=false,
  title={\spacedcaps{an illustration}\hfill\spacedcaps{fictional}},
  coltitle=softink, colbacktitle=white, toptitle=4pt, bottomtitle=0pt,
  titlerule=0pt,
  fontupper=\fontsize{10.75}{14.75}\selectfont}

% ---------------------------------------------------------------------------
% Table of contents
% ---------------------------------------------------------------------------
\renewcommand{\contentsname}{Contents}
\renewcommand{\printtoctitle}[1]{\centering\displayfont\fontsize{23}{29}\selectfont #1}
\renewcommand{\aftertoctitle}{\par\nobreak\vskip 10pt{\centering\ornament\par}\vskip 26pt}
\setlength{\cftbeforechapterskip}{4.5pt plus 1pt}
\setlength{\cftbeforepartskip}{14pt plus 2pt}
\renewcommand{\cftchapterfont}{\normalfont}
\renewcommand{\cftchapterpagefont}{\liningfont}
\renewcommand{\cftchapterleader}{\hfill}
\renewcommand{\cftchapterafterpnum}{}
\setlength{\cftchapternumwidth}{1.9em}
\renewcommand{\cftchapterpresnum}{\liningfont}
\renewcommand{\cftpartfont}{\small\capsfont\lsstyle}
\renewcommand{\cftpartpagefont}{\liningfont}
\renewcommand{\cftpartleader}{\hfill}
\renewcommand{\cftpartpresnum}{}
\setlength{\cftpartnumwidth}{0pt}
% Ragged right so long part and chapter titles never stretch across the line.
\setrmarg{3.2em plus 1fil}
\setpnumwidth{2.2em}
\renewcommand{\cftdot}{}
\renewcommand*{\cftpartname}{}
\renewcommand{\partnumberline}[1]{}

% ---------------------------------------------------------------------------
% PDF: KDP wants no bookmarks, links, or annotations in a print interior.
% Plain URLs are typeset with the url package; metadata goes in the info dict.
% ---------------------------------------------------------------------------
\RequirePackage{url}
\urlstyle{same}
\def\UrlBreaks{\do\/\do-\do.\do\_\do\=\do\&\do\?}
\Urlmuskip=0mu plus 1.5mu
\newcommand{\href}[2]{#2}
\newcommand{\setpdfinfo}[3]{\pdfextension info{/Title (#1) /Author (#2) /Subject (#3) /Creator (LuaLaTeX fine-book)}}

% Folio style used on the copyright and dedication pages
\newcommand{\frontpage}{\clearpage\thispagestyle{empty}}
