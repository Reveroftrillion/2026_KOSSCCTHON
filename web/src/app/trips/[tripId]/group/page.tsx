import GroupPreferenceView from '@/components/fe2/GroupPreferenceView'

export default async function GroupPreferencePage({ params }: PageProps<'/trips/[tripId]/group'>) {
  const { tripId } = await params
  return <GroupPreferenceView tripId={tripId} />
}
