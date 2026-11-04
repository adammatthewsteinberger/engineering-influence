% Hardcover variant of fine-book.cls for a one-volume KDP hardcover.
% It uses the identical generated text and 6 x 9 trim, with a denser but
% still readable page design.  This file changes layout only.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{fine-book-hardcover}[2026/11/01 Fine book hardcover interior]

\input{fine-book.cls}

% KDP's 550-page hardcover limit makes blank verso pages materially costly.
% The text is unchanged; chapters may begin on the next available page.
\openany

% Hardcover interior: retain the KDP gutter tier for 501--550 pages while
% using the available outer/live area more efficiently.
\setlrmarginsandblock{0.75in}{0.38in}{*}
\setulmarginsandblock{0.58in}{0.62in}{*}
\setheadfoot{14pt}{20pt}
\setheaderspaces{*}{12pt}{*}
\checkandfixthelayout[fixed]

% A compact Garamond setting.  No manuscript content is removed or rewritten.
\renewcommand{\normalsize}{\fontsize{9.7}{12.2}\selectfont}
\normalsize
\setlength{\parindent}{1.05em}
\setlength{\emergencystretch}{1.1em}
\setlist{itemsep=0.16\baselineskip, topsep=0.30\baselineskip, parsep=0pt,
  leftmargin=1.35em}

% Reduce ornamental page consumption while preserving hierarchy.
\makechapterstyle{fine-hardcover}{%
  \setlength{\beforechapskip}{0.30in}
  \setlength{\midchapskip}{12pt}
  \setlength{\afterchapskip}{25pt}
  \renewcommand{\chapnamefont}{\spacedcaps}
  \renewcommand{\chapnumfont}{\spacedcaps}
  \renewcommand{\chaptitlefont}{\displayfont\fontsize{19}{23}\selectfont}
  \renewcommand{\printchaptername}{}
  \renewcommand{\chapternamenum}{}
  \renewcommand{\printchapternum}{\centering
    {\small\chapnamefont{chapter \bookNumberWord{\value{chapter}}}}}
  \renewcommand{\afterchapternum}{\par\nobreak\vskip\midchapskip}
  \renewcommand{\printchapternonum}{\centering\vphantom{\chapnamefont{chapter}}%
    \par\nobreak\vskip\midchapskip}
  \renewcommand{\printchaptertitle}[1]{%
    \centering\begin{minipage}{0.92\textwidth}\centering\chaptitlefont ##1\end{minipage}%
    \par\nobreak\vskip 10pt\ornament}
  \renewcommand{\afterchaptertitle}{\par\nobreak\vskip\afterchapskip}
}
\chapterstyle{fine-hardcover}

\setsecheadstyle{\displayfont\fontsize{12.5}{15}\selectfont\raggedright}
\setbeforesecskip{-1.35\baselineskip plus -0.3\baselineskip minus -0.15\baselineskip}
\setaftersecskip{0.55\baselineskip plus 0.1\baselineskip}
\setsubsecheadstyle{\displayfont\itshape\fontsize{11}{13.5}\selectfont\raggedright}
\setbeforesubsecskip{-1.05\baselineskip plus -0.25\baselineskip minus -0.1\baselineskip}
\setaftersubsecskip{0.30\baselineskip plus 0.1\baselineskip}

\renewcommand{\printtoctitle}[1]{\centering\displayfont\fontsize{19}{23}\selectfont #1}
\renewcommand{\aftertoctitle}{\par\nobreak\vskip 7pt{\centering\ornament\par}\vskip 15pt}
\setlength{\cftbeforechapterskip}{2.5pt plus 0.5pt}
\setlength{\cftbeforepartskip}{9pt plus 1pt}

