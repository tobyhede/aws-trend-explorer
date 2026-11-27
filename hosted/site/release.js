// The one place the hosted explorer reads its release from. A new release changes these values,
// and product_change/public_dataset.py writes the matching dated file into data/.
export const RELEASE = {
  date: '2026-11-27',   // release date; names the public dataset file
  first: '2010-01-01',  // start of the collection period
  cutoff: '2026-10-28', // collection cutoff; also the last day of the matched period in every year
};
export const DATASET = `data/aws-announcements-${RELEASE.date}.parquet`;
