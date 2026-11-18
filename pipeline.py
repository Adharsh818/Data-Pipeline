import pandas as pd


def clean_data(df):

    raw = df.drop_duplicates().copy()
    compact = raw.replace(r"\s+", "", regex=True)
    df = compact.replace("", pd.NA)

    name = df["Name"].str.replace(r"""['"/\\]""", "", regex=True)
    df["Name"] = name.str.capitalize().where(name.str.isalpha())

    gender = df["Gender"].str.lower()
    df["Gender"] = gender.map({
        "m": "Male", "male": "Male",
        "f": "Female", "female": "Female",
        "0": "Unknown", "1": "Unknown",
    }).astype("string")

    df["Grade"] = df["Grade"].str.lower().str.removeprefix("grade")
    for col in ["Math", "Science", "English", "Total"]:
        df[col] = df[col].str.lower().str.removesuffix("marks")

    limits = {
        "Grade": (1, 12),
        "Math": (0, 100),
        "Science": (0, 100),
        "English": (0, 100),
        "Total": (0, 300),
    }

    for col, (minimum, maximum) in limits.items():
        number = pd.to_numeric(df[col], errors="coerce")
        valid = number.between(minimum, maximum) & number.mod(1).eq(0)
        df[col] = number.where(valid).astype("Int64")

    # Record blanks, invalid values, and unmapped gender codes.
    errors = ("Invalid: " + raw).where(df.isna())
    errors = errors.mask(compact.eq(""), "Blank")
    errors.loc[gender.isin(["0", "1"]), "Gender"] = "Unmapped code: " + gender

    # Check the recorded total against the three subject marks.
    subject_total = df[["Math", "Science", "English"]].sum(axis=1, min_count=3)
    mismatch = df["Total"].ne(subject_total).fillna(False)
    errors.loc[mismatch, "Total"] = "Total differs from subject sum"

    return df, errors.dropna(how="all")


def transform_data(df):
    df = df.copy()
    subjects = ["Math", "Science", "English"]

    df["Average_Mark"] = df[subjects].mean(axis=1, skipna=False).round(2)

    below_50 = df[subjects].lt(50).any(axis=1)
    df["Any_Subject_Below_50"] = below_50.astype("Int64").where(
        df["Average_Mark"].notna()
    )

    return df


def analyze_data(df):
    columns = ["Math", "Science", "English", "Average_Mark"]
    by_grade = df.groupby("Grade")

    summary = by_grade[columns].mean()
    summary["Pct_Any_Subject_Below_50"] = (
        by_grade["Any_Subject_Below_50"].mean() * 100
    )

    return summary.round(2)


def run_pipeline():
    df = pd.read_csv(
        "student_data_combined.csv",
        dtype="string",
        keep_default_na=False,
    )

    df, errors = clean_data(df)
    df = transform_data(df)
    grade_summary = analyze_data(df)

    df.to_csv("student_data_cleaned.csv", index=False)
    errors.to_csv("student_data_cleaning_errors.csv", index_label="Source_Row_Index")
    print(df.head(10).to_string())
    print(grade_summary.to_string())
    print(f"\nSaved {len(df):,} cleaned rows and {len(errors):,} flagged rows.")


if __name__ == "__main__":
    run_pipeline()